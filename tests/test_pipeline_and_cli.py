"""Tests for bgchange/pipeline.py (change_background) and bgchange/cli.py (the command).

The real AI model is replaced by FakeModel: it says "the subject is the square in
the middle". So these tests need no GPU and no downloaded weights, and they check
the wiring (options, errors, file names), not the AI.
"""

import numpy as np
import pytest
from PIL import Image

import bgchange.pipeline as pipeline
from bgchange.cli import main
from bgchange.s1_load_photo import ImageLoadError
from bgchange.s2_read_color import Color, ColorParseError
from bgchange.s3_ai_models import Segmenter


class FakeModel(Segmenter):
    name = "fake"

    def predict(self, image):
        mask = np.zeros((image.height, image.width), np.float32)
        mask[image.height // 4 : 3 * image.height // 4, image.width // 4 : 3 * image.width // 4] = 1.0
        return mask


@pytest.fixture(autouse=True)
def fake_model(monkeypatch):
    """Every test in this file gets FakeModel instead of the real AI."""
    monkeypatch.setattr(pipeline, "get_segmenter", lambda name, device: FakeModel())


@pytest.fixture
def photo_path(tmp_path):
    path = tmp_path / "shoe.png"
    Image.new("RGB", (80, 60), (200, 30, 30)).save(path)
    return path


# --- change_background() -----------------------------------------------------


def test_result_has_the_image_colour_and_timings(photo_path):
    result = pipeline.change_background(photo_path, "#00FF00")
    assert result.image.size == (80, 60) and result.image.mode == "RGB"
    assert result.color == Color(0, 255, 0)
    assert np.asarray(result.image)[0, 0].tolist() == [0, 255, 0]  # corner = background = new colour
    assert set(result.timings) == {"load_model", "mask", "shadow", "blend"}


def test_accepts_bytes_like_an_upload(photo_path):
    result = pipeline.change_background(photo_path.read_bytes(), "#00FF00")
    assert result.image.size == (80, 60)


def test_transparent_colour_gives_rgba(photo_path):
    assert pipeline.change_background(photo_path, "#00000000").image.mode == "RGBA"


def test_bad_colour_fails_before_the_model_is_loaded(photo_path, monkeypatch):
    def must_not_load(name, device):
        raise AssertionError("the model was loaded for a bad colour")

    monkeypatch.setattr(pipeline, "get_segmenter", must_not_load)
    with pytest.raises(ColorParseError):
        pipeline.change_background(photo_path, "#GG0000")


def test_bad_file_is_an_image_load_error(tmp_path):
    with pytest.raises(ImageLoadError):
        pipeline.change_background(tmp_path / "missing.jpg", "#FFFFFF")


@pytest.mark.parametrize(("option", "value"), [("shadow", "soft"), ("shadow_strength", 1.5)])
def test_bad_shadow_options_are_refused(photo_path, option, value):
    with pytest.raises(ValueError):
        pipeline.change_background(photo_path, "#FFFFFF", **{option: value})


# --- the bgchange command ------------------------------------------------------


def test_command_saves_to_the_given_file(photo_path, tmp_path, capsys):
    main([str(photo_path), "--color", "#FF0066", "-o", str(tmp_path / "out.png")])
    assert Image.open(tmp_path / "out.png").size == (80, 60)
    assert "saved" in capsys.readouterr().out


def test_command_default_name_includes_colour_and_options(photo_path, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # outputs/ is created in the current folder
    main([str(photo_path), "--color", "#FF0066"])
    main([str(photo_path), "--color", "#FF0066", "--shadow", "mix"])
    assert (tmp_path / "outputs" / "shoe_on_FF0066.png").exists()
    assert (tmp_path / "outputs" / "shoe_on_FF0066_shadow-mix.png").exists()


def test_command_bad_colour_is_one_clear_line(photo_path):
    with pytest.raises(SystemExit, match="not a hex colour"):
        main([str(photo_path), "--color", "red"])


def test_command_refuses_strength_outside_0_1(photo_path):
    with pytest.raises(SystemExit):  # argparse exits with a usage message
        main([str(photo_path), "--color", "#FFFFFF", "--shadow-strength", "2"])


# --- a picture as the background ---------------------------------------------


@pytest.fixture
def picture_path(tmp_path):
    """A blue 200x100 picture: wider than the photo, so it is cropped."""
    path = tmp_path / "beach.png"
    Image.new("RGB", (200, 100), (0, 0, 255)).save(path)
    return path


def test_picture_background_fills_around_the_subject(photo_path, picture_path):
    result = pipeline.change_background(photo_path, background_image=picture_path, shadow="none")
    pixels = np.asarray(result.image)
    assert result.image.size == (80, 60) and result.color is None
    assert tuple(pixels[2, 2]) == (0, 0, 255)  # outside FakeModel's square: the picture
    assert tuple(pixels[30, 40]) == (200, 30, 30)  # inside: the photo


def test_picture_background_from_bytes_like_an_upload(photo_path, picture_path):
    result = pipeline.change_background(photo_path.read_bytes(), background_image=picture_path.read_bytes())
    assert result.image.size == (80, 60)


def test_exactly_one_background_is_required(photo_path, picture_path):
    with pytest.raises(ValueError, match="exactly one"):
        pipeline.change_background(photo_path)
    with pytest.raises(ValueError, match="exactly one"):
        pipeline.change_background(photo_path, "#FFFFFF", background_image=picture_path)


def test_broken_background_picture_fails_before_the_model(photo_path, tmp_path, monkeypatch):
    def no_model(name, device):
        raise AssertionError("the model must not be loaded for a broken background")

    monkeypatch.setattr(pipeline, "get_segmenter", no_model)
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"not an image")
    with pytest.raises(ImageLoadError):
        pipeline.change_background(photo_path, background_image=broken)


def test_command_background_picture_default_name(photo_path, picture_path, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    main([str(photo_path), "--background", str(picture_path)])
    assert (tmp_path / "outputs" / "shoe_on_beach.png").exists()
    assert "picture:" in capsys.readouterr().out


def test_command_refuses_colour_and_picture_together(photo_path, picture_path):
    with pytest.raises(SystemExit):  # argparse: the two options are mutually exclusive
        main([str(photo_path), "--color", "#FFFFFF", "--background", str(picture_path)])
