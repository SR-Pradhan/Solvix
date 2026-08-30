import io

import pytest
from PIL import Image

from app.services.profile_service import (
    AVATAR_MIME,
    AVATAR_SIZE,
    MAX_UPLOAD_BYTES,
    ProfileError,
    clean_display_name,
    normalise_avatar,
    validate_new_password,
    validate_size,
    validate_type,
    validate_upload,
)


def encode(image: Image.Image, fmt: str = "PNG") -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


class TestDisplayName:
    def test_surrounding_and_repeated_spaces_collapse(self):
        assert clean_display_name("  Sruti   Ranjan ") == "Sruti Ranjan"

    def test_blank_becomes_none_rather_than_empty_string(self):
        # Otherwise "" and NULL both render as no name but compare differently.
        assert clean_display_name("   ") is None
        assert clean_display_name("") is None

    def test_missing_stays_missing(self):
        assert clean_display_name(None) is None

    def test_overlong_name_is_rejected(self):
        with pytest.raises(ProfileError, match="longer than"):
            clean_display_name("a" * 101)

    def test_length_is_measured_after_trimming(self):
        assert clean_display_name(" " + "a" * 100 + " ") == "a" * 100


class TestPassword:
    def test_short_password_is_rejected(self):
        with pytest.raises(ProfileError, match="at least 8"):
            validate_new_password("short12", "current-password")

    def test_reusing_the_current_password_is_rejected(self):
        with pytest.raises(ProfileError, match="different"):
            validate_new_password("same-password", "same-password")

    def test_valid_password_is_returned_unchanged(self):
        assert validate_new_password("a-new-password", "old") == "a-new-password"


class TestUploadEnvelope:
    def test_non_image_type_is_rejected(self):
        with pytest.raises(ProfileError, match="PNG, JPEG or WebP"):
            validate_upload("application/pdf", 1000)

    def test_missing_type_is_rejected(self):
        with pytest.raises(ProfileError):
            validate_upload(None, 1000)

    def test_oversized_upload_is_rejected_before_decoding(self):
        with pytest.raises(ProfileError, match="smaller than"):
            validate_upload("image/png", MAX_UPLOAD_BYTES + 1)

    def test_empty_file_is_rejected(self):
        with pytest.raises(ProfileError, match="empty"):
            validate_upload("image/png", 0)

    def test_accepted_types_pass(self):
        for mime in ("image/png", "image/jpeg", "image/webp"):
            validate_upload(mime, 1000)


class TestNormaliseAvatar:
    def test_output_is_a_square_jpeg_at_the_target_size(self):
        data, mime = normalise_avatar(encode(Image.new("RGB", (900, 900), "red")))

        assert mime == AVATAR_MIME
        assert Image.open(io.BytesIO(data)).size == (AVATAR_SIZE, AVATAR_SIZE)

    def test_a_small_image_is_scaled_up_rather_than_left_ragged(self):
        data, _ = normalise_avatar(encode(Image.new("RGB", (40, 40), "blue")))

        assert Image.open(io.BytesIO(data)).size == (AVATAR_SIZE, AVATAR_SIZE)

    def test_portrait_photo_is_cropped_from_the_middle(self):
        # A tall image with a distinct band across its centre: after a centre
        # crop that band should survive, which a top-left crop would lose.
        image = Image.new("RGB", (200, 600), "black")
        image.paste(Image.new("RGB", (200, 200), "white"), (0, 200))

        data, _ = normalise_avatar(encode(image))
        result = Image.open(io.BytesIO(data))

        assert result.getpixel((AVATAR_SIZE // 2, AVATAR_SIZE // 2)) == (255, 255, 255)

    def test_landscape_photo_is_cropped_from_the_middle(self):
        image = Image.new("RGB", (600, 200), "black")
        image.paste(Image.new("RGB", (200, 200), "white"), (200, 0))

        data, _ = normalise_avatar(encode(image))
        result = Image.open(io.BytesIO(data))

        assert result.getpixel((AVATAR_SIZE // 2, AVATAR_SIZE // 2)) == (255, 255, 255)

    def test_transparency_is_flattened_onto_white_not_black(self):
        # JPEG has no alpha channel. Without an explicit background the
        # transparent pixels would come back black.
        data, _ = normalise_avatar(encode(Image.new("RGBA", (300, 300), (0, 0, 0, 0))))
        result = Image.open(io.BytesIO(data))

        assert result.getpixel((AVATAR_SIZE // 2, AVATAR_SIZE // 2)) == (255, 255, 255)

    def test_palette_image_is_accepted(self):
        data, _ = normalise_avatar(
            encode(Image.new("RGB", (300, 300), "green").convert("P"))
        )

        assert Image.open(io.BytesIO(data)).size == (AVATAR_SIZE, AVATAR_SIZE)

    def test_bytes_that_are_not_an_image_are_rejected(self):
        # A renamed script arriving with an image Content-Type gets this far,
        # so the decode is the real check, not the header.
        with pytest.raises(ProfileError, match="not an image"):
            normalise_avatar(b"#!/bin/sh\nrm -rf /\n")

    def test_truncated_image_is_rejected(self):
        whole = encode(Image.new("RGB", (300, 300), "red"))

        with pytest.raises(ProfileError):
            normalise_avatar(whole[: len(whole) // 3])

    def test_exif_is_not_carried_into_the_stored_image(self):
        # Phone photos embed GPS coordinates; re-encoding is what drops them.
        source = Image.new("RGB", (400, 400), "red")
        exif = source.getexif()
        exif[0x010F] = "Solvix Test Camera"

        buffer = io.BytesIO()
        source.save(buffer, format="JPEG", exif=exif)

        data, _ = normalise_avatar(buffer.getvalue())

        assert not Image.open(io.BytesIO(data)).getexif()

    def test_a_large_photo_shrinks_to_a_storable_size(self):
        data, _ = normalise_avatar(encode(Image.new("RGB", (3000, 2000), "red")))

        assert len(data) < 100 * 1024


# --- the LeetCode repository reference ---

from app.services.profile_service import clean_repo


def test_a_plain_owner_repo_is_kept():
    assert clean_repo("SR-Pradhan/LeetCode-Problems") == "SR-Pradhan/LeetCode-Problems"


def test_a_pasted_github_url_is_reduced_to_owner_repo():
    # What people actually paste, rather than what the field asks for.
    assert (
        clean_repo("https://github.com/SR-Pradhan/LeetCode-Problems")
        == "SR-Pradhan/LeetCode-Problems"
    )


def test_a_git_suffix_and_trailing_slash_come_off():
    assert clean_repo("github.com/owner/repo.git") == "owner/repo"
    assert clean_repo("owner/repo/") == "owner/repo"


def test_clearing_the_repo_is_allowed():
    # Unlike the Codeforces handle, disconnecting LeetCode is legitimate: the
    # dashboard treats a missing handle as "not set up", but a missing repo
    # simply means no LeetCode.
    assert clean_repo("") is None
    assert clean_repo("   ") is None
    assert clean_repo(None) is None


def test_something_that_is_not_a_repository_is_refused():
    for bad in ("nope", "owner", "owner/repo/extra", "owner repo"):
        with pytest.raises(ProfileError):
            clean_repo(bad)


# --- decompression bombs ---------------------------------------------------
#
# The size limit says how big the *file* is, not what it expands to. A valid
# 138-byte PNG can declare 60000x60000 and cost gigabytes to decode. Pillow
# raises DecompressionBombError for the worst of them, but that inherits from
# Exception rather than OSError, so it escaped the handler and became a 500.


def _png_declaring(width: int, height: int) -> bytes:
    """A structurally valid greyscale PNG header claiming huge dimensions."""
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"\x00" + b"\x00" * width, 9))
        + chunk(b"IEND", b"")
    )


def test_a_tiny_file_declaring_a_huge_image_is_refused():
    bomb = _png_declaring(60000, 60000)
    # It is small enough to pass every envelope check, which is the point.
    validate_upload("image/png", len(bomb))
    with pytest.raises(ProfileError):
        normalise_avatar(bomb)


def test_an_image_over_the_pixel_limit_is_refused():
    with pytest.raises(ProfileError):
        normalise_avatar(_png_declaring(9000, 9000))


def test_the_envelope_halves_can_be_checked_separately():
    """The upload route judges the declared type before reading any bytes."""
    with pytest.raises(ProfileError):
        validate_type("application/pdf")
    assert validate_type("image/png") is None

    with pytest.raises(ProfileError):
        validate_size(MAX_UPLOAD_BYTES + 1)
    with pytest.raises(ProfileError):
        validate_size(0)
    assert validate_size(1000) is None
