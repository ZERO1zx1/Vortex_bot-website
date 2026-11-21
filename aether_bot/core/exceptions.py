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


class InvalidBetError(ValidationError):
    user_message = "✦ Бооцооны дүн буруу байна."


class InsufficientFundsError(AetherError):
    user_message = "✦ Wallet дээр хангалттай Aether Coin байхгүй."


class InsufficientInventoryError(AetherError):
    user_message = "✦ Inventory дээр энэ item хангалттай байхгүй."


class ItemNotFoundError(AetherError):
    user_message = "✦ Ийм item Aether дэлгүүрт бүртгэгдээгүй байна."


class ItemNotUsableError(AetherError):
    user_message = "✦ Энэ item-ийг одоо ашиглах боломжгүй."


class TargetProtectedError(AetherError):
    user_message = "✦ Зорилт нь Aether Shield-ээр хамгаалагдсан байна."


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


class ActionCooldownError(AetherError):
    user_message = "✦ Уг үйлдэл хараахан бэлэн болоогүй байна."

    def __init__(self, action: str, remaining_sec: int):
        self.action = action
        self.remaining_sec = max(0, int(remaining_sec))
        super().__init__(
            f"✦ **{action}** дахин хийхэд "
            f"`{humanize_seconds(self.remaining_sec)}` үлдсэн."
        )


class JailedError(AetherError):
    user_message = "✦ Та шоронд байна."

    def __init__(self, remaining_sec: int, bail_cost: int = 0):
        self.remaining_sec = max(0, int(remaining_sec))
        self.bail_cost = max(0, int(bail_cost))
        line = (
            f"✦ Та шоронд байна. Гарах хүртэл "
            f"`{humanize_seconds(self.remaining_sec)}` үлдсэн."
        )
        if self.bail_cost > 0:
            line += f" Батлан даалт: **{self.bail_cost:,}** ⛃."
        super().__init__(line)


class AlreadyJailedError(AetherError):
    user_message = "✦ Та аль хэдийн шоронд байна."


class NotJailedError(AetherError):
    user_message = "✦ Та шоронд биш байна."


class GameStateError(AetherError):
    user_message = "✦ Тоглоомын төлөв буруу байна. Дахин эхлүүлнэ үү."


class JobNotFoundError(AetherError):
    user_message = "✦ Ийм ажил байхгүй эсвэл таны түвшинд нээгдээгүй байна."


class CrimeNotFoundError(AetherError):
    user_message = "✦ Ийм гэмт хэрэг байхгүй эсвэл таны түвшинд нээгдээгүй байна."


class DungeonNotFoundError(AetherError):
    user_message = "✦ Ийм dungeon байхгүй эсвэл таны түвшинд нээгдээгүй байна."


class BossNotFoundError(AetherError):
    user_message = "✦ Ийм boss байхгүй эсвэл таны түвшинд нээгдээгүй байна."
