"""Aether-ийн домайн алдаанууд.

Дүрэм: service давхарга зөвхөн эдгээр exception-ыг шиднэ, UI давхарга
`user_message`-ийг embed-ийн тайлбар болгон шууд харуулна.
"""

from __future__ import annotations

from utils.time_utils import humanize_seconds


class AetherError(Exception):
    """Бүх домайн алдааны суурь класс."""

    user_message = "✦ Ямар нэгэн зүйл буруугаар эргэлдлээ. Дараа дахин оролдоно уу."
    color_attr = "DANGER"

    def __init__(self, user_message: str | None = None, *, detail: str | None = None):
        self.detail = detail
        if user_message:
            self.user_message = user_message
        super().__init__(self.detail or self.user_message)


class ValidationError(AetherError):
    user_message = "✦ Өгөгдөл буруу байна. Утгыг шалгаад дахин илгээнэ үү."


class InvalidAmountError(ValidationError):
    user_message = "✦ Дүн 0-ээс их бүхэл тоо байх ёстой."


class InsufficientFundsError(AetherError):
    user_message = "✦ Wallet дээр хангалттай Aether Coin байхгүй."


class CooldownError(AetherError):
    user_message = "✦ Уг үйлдэл хараахан бэлэн болоогүй байна."

    def __init__(self, skill_name: str, remaining_sec: int):
        self.remaining_sec = max(0, int(remaining_sec))
        super().__init__(
            f"✦ **{skill_name}** дахин ашиглахад "
            f"`{humanize_seconds(self.remaining_sec)}` үлдсэн."
        )


class SkillNotFoundError(AetherError):
    user_message = "✦ Ийм skill Aether системд бүртгэгдээгүй байна."


class SkillLockedError(AetherError):
    user_message = "✦ Энэ skill-ийг нээхэд таны түвшин хангалтгүй."


class SkillMaxedError(AetherError):
    user_message = "✦ Энэ skill аль хэдийн дээд түвшиндээ хүрсэн."


class SkillNotActiveTypeError(AetherError):
    user_message = "✦ Энэ skill идэвхтэй (Active) төрөлд хамаарахгүй."


class SkillNotUsableError(AetherError):
    user_message = "✦ Энэ skill-ийг ашиглахын тулд эхлээд сайжруулна уу."


class InsufficientSkillPointsError(AetherError):
    user_message = "✦ Skill Point (SP) хангалтгүй байна."


class UserNotFoundError(AetherError):
    user_message = "✦ Тоглогч Aether системд бүртгэгдээгүй байна."


class PermissionDeniedError(AetherError):
    user_message = "✦ Энэ цэс зөвхөн эзэндээ нээлттэй."


class SessionExpiredError(AetherError):
    user_message = "✦ Хугацаа дууссан. Командыг дахин ажиллуулна уу."


class RateLimitedError(AetherError):
    user_message = "✦ Discord API-ийн хязгаарт хүрлээ. Хэсэг хүлээнэ үү."
