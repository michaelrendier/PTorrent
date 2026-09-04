"""Percentage-based screen geometry.

Every rectangle is expressed as a fraction of its parent, resolved against the
live terminal size on each repaint, then clamped to sane minimums. A full-screen
terminal and an 80x24 one lay out from the same numbers.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    y: int
    x: int
    h: int
    w: int

    # ── constructors ──
    @staticmethod
    def screen(stdscr) -> "Rect":
        my, mx = stdscr.getmaxyx()
        return Rect(0, 0, my, mx)

    def pct(self, x0: float, y0: float, x1: float, y1: float,
            min_w: int = 1, min_h: int = 1) -> "Rect":
        """Sub-rectangle from fractional edges (0.0-1.0) of this rect."""
        nx = self.x + round(self.w * x0)
        ny = self.y + round(self.h * y0)
        nw = max(min_w, round(self.w * (x1 - x0)))
        nh = max(min_h, round(self.h * (y1 - y0)))
        nw = min(nw, self.x + self.w - nx)
        nh = min(nh, self.y + self.h - ny)
        return Rect(ny, nx, max(min_h, nh), max(min_w, nw))

    def inset(self, dy: int, dx: int) -> "Rect":
        return Rect(self.y + dy, self.x + dx,
                    max(1, self.h - 2 * dy), max(1, self.w - 2 * dx))

    def rows(self, top_h: int) -> tuple["Rect", "Rect"]:
        top_h = max(0, min(top_h, self.h))
        return (Rect(self.y, self.x, top_h, self.w),
                Rect(self.y + top_h, self.x, self.h - top_h, self.w))

    def cols(self, right_w: int) -> tuple["Rect", "Rect"]:
        right_w = max(0, min(right_w, self.w))
        return (Rect(self.y, self.x, self.h, self.w - right_w),
                Rect(self.y, self.x + self.w - right_w, self.h, right_w))

    # ── helpers ──
    @property
    def bottom(self) -> int:
        return self.y + self.h

    @property
    def right(self) -> int:
        return self.x + self.w

    def contains(self, y: int, x: int) -> bool:
        return self.y <= y < self.bottom and self.x <= x < self.right


def sidebar_width(total_w: int, collapsed: bool) -> int:
    """Legacy-BIOS 'Item Specific Help' panel.

    collapsed / narrow  -> 0 (a one-line hint shows in the status bar instead)
    normal              -> ~26% clamped to [26, 44]
    large geometry      -> grows to ~30% clamped to 60
    """
    if collapsed or total_w < 90:
        return 0
    if total_w > 170:
        return min(60, round(total_w * 0.30))
    return max(26, min(44, round(total_w * 0.26)))
