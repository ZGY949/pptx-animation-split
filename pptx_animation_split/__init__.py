"""Expose the maintained Skill engine when running from a source checkout."""

from pathlib import Path

__path__ = [str(Path(__file__).resolve().parents[1] / "skills/pptx-animation-split/scripts/pptx_animation_split")]

from ._version import __version__
