"""Account profile rules: display name, password change and avatar images.

Everything here is a pure function over its arguments. The endpoints do the
database work; this module only decides what is allowed and what the stored
bytes should look like, which is what makes it testable without a server, a
database or a real upload.
"""

from __future__ import annotations

import io
import re

from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError

MAX_DISPLAY_NAME = 100
MIN_PASSWORD_LENGTH = 8

# Rejected before the bytes are read, so an oversized upload never has to be
# decoded. Generous: phone cameras produce 3-8MB photos routinely.
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
ACCEPTED_UPLOAD_TYPES = ("image/png", "image/jpeg", "image/webp")

# Checked against the header before anything is decoded. A valid 138-byte PNG
# can declare 60000x60000 and cost gigabytes of memory to expand — the file
# size limit above says nothing about what the file expands *to*. Generous
# next to a phone camera, which tops out around 50MP.
MAX_IMAGE_PIXELS = 50_000_000

# Displayed at 40px in the topbar and 96px on the profile page. 256 covers
# both on a retina screen with nothing spare.
AVATAR_SIZE = 256
AVATAR_MIME = "image/jpeg"
AVATAR_QUALITY = 85


class ProfileError(ValueError):
    """A rule the user broke, phrased for them rather than for a log."""


def clean_display_name(value: str | None) -> str | None:
    """Trim a submitted name, treating blank as "no name" rather than "".

    An empty string and NULL would render identically but sort and compare
    differently, so only one of them is allowed to reach the database.
    """
    if value is None:
        return None

    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    if len(cleaned) > MAX_DISPLAY_NAME:
        raise ProfileError(f"Name cannot be longer than {MAX_DISPLAY_NAME} characters")
    return cleaned


# "owner/repo", the only shape GitHub's API accepts. Anything else is a typo
# that would otherwise be stored and only surface as a failed import later.
REPO_PATTERN = re.compile(r"^[\w.-]+/[\w.-]+$")


def clean_repo(value: str | None) -> str | None:
    """Normalise a GitHub repository reference, or refuse it.

    Accepts what people actually paste — a full URL, a trailing `.git` — and
    stores the canonical `owner/repo`. Clearing it is allowed: disconnecting
    LeetCode is a legitimate thing to want, unlike clearing the Codeforces
    handle, which the dashboard treats as "not set up yet".
    """
    if value is None:
        return None

    trimmed = value.strip()
    if not trimmed:
        return None

    # The scheme is optional because browsers hide it, so what people copy out
    # of the address bar is "github.com/owner/repo".
    trimmed = re.sub(r"^(https?://)?(www\.)?github\.com/", "", trimmed, flags=re.I)
    trimmed = re.sub(r"\.git$", "", trimmed).strip("/")

    if not REPO_PATTERN.match(trimmed):
        raise ProfileError("Use the owner/repo form, e.g. your-name/LeetCode-Problems")
    return trimmed


def validate_new_password(new_password: str, current_password: str) -> str:
    """Check a replacement password without knowing anything about hashing."""
    if len(new_password) < MIN_PASSWORD_LENGTH:
        raise ProfileError(
            f"New password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
    if new_password == current_password:
        raise ProfileError("New password must be different from the current one")
    return new_password


def validate_type(content_type: str | None) -> None:
    """The half of the envelope that can be judged before reading a byte."""
    if content_type not in ACCEPTED_UPLOAD_TYPES:
        raise ProfileError("Photo must be a PNG, JPEG or WebP image")


def validate_size(size: int) -> None:
    if size > MAX_UPLOAD_BYTES:
        mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise ProfileError(f"Photo must be smaller than {mb}MB")
    if size == 0:
        raise ProfileError("That file is empty")


def validate_upload(content_type: str | None, size: int) -> None:
    """Reject an upload on its envelope, before the bytes are decoded."""
    validate_type(content_type)
    validate_size(size)


def normalise_avatar(raw: bytes) -> tuple[bytes, str]:
    """Turn an arbitrary upload into a square 256px JPEG.

    Re-encoding rather than storing the original does three jobs at once: it
    caps what a row costs, it discards EXIF (which carries GPS coordinates from
    a phone photo), and it proves the bytes really decode as an image instead
    of trusting a Content-Type header the client chose.
    """
    try:
        image = Image.open(io.BytesIO(raw))
        # On the header, before load() decodes anything. Pillow raises
        # DecompressionBombError for the truly absurd, but it inherits from
        # Exception rather than OSError, so it escaped the handler below and
        # became a 500 instead of a refusal.
        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise ProfileError("That image is too large for Solvix to process")
        image.load()
    except (UnidentifiedImageError, OSError, DecompressionBombError) as exc:
        raise ProfileError("That file is not an image Solvix can read") from exc

    # Flattened onto white: a transparent PNG saved as JPEG would otherwise
    # come back with black wherever it used to be see-through.
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        canvas = Image.new("RGB", image.size, (255, 255, 255))
        canvas.paste(image, mask=image.split()[-1])
        image = canvas
    else:
        image = image.convert("RGB")

    image = _centre_square(image)
    image = image.resize((AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS)

    out = io.BytesIO()
    image.save(out, format="JPEG", quality=AVATAR_QUALITY, optimize=True)
    return out.getvalue(), AVATAR_MIME


def _centre_square(image: Image.Image) -> Image.Image:
    """Crop to the middle square, so a portrait photo keeps the face."""
    width, height = image.size
    if width == height:
        return image

    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))
