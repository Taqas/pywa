import dataclasses
import random
from typing import Callable, TypeVar

from pywa import filters as fil, WhatsApp
from pywa.errors import WhatsAppError, MediaUploadError
from pywa.types import (
    Message,
    CallbackSelection,
    CallbackButton,
    MessageStatus,
    TemplateStatus,
)
from pywa.types.base_update import BaseUpdate
from tests.common import UPDATES, API_VERSIONS, WA_NO_FILTERS

_T = TypeVar("_T", bound=BaseUpdate)


def same(x: _T) -> _T:
    return x


# {filename: {test_name: [(update_modifier, filter_func)]}}

FILTERS: dict[
    str, dict[str, list[tuple[Callable[[_T], _T], Callable[[WhatsApp, _T], bool]]]]
] = {
    "message": {
        "text": [
            (same, fil.text),
            (lambda m: modify_text(m, "hello"), fil.text.matches("hello")),
            (
                lambda m: modify_text(m, "hello"),
                fil.text.matches("hello", ignore_case=True),
            ),
            (lambda m: modify_text(m, "hi hello"), fil.text.contains("hello")),
            (
                lambda m: modify_text(m, "hi Hello"),
                fil.text.contains("hello", "Hi", ignore_case=True),
            ),
            (
                lambda m: modify_text(m, "hi bye"),
                fil.text.startswith("hi"),
            ),
            (
                lambda m: modify_text(m, "hi bye"),
                fil.text.startswith("Hi", ignore_case=True),
            ),
            (
                lambda m: modify_text(m, "hi bye"),
                fil.text.endswith("bye"),
            ),
            (
                lambda m: modify_text(m, "hi bye"),
                fil.text.endswith("Bye", ignore_case=True),
            ),
            (
                lambda m: modify_text(m, "hi bye"),
                fil.text.regex(r"^hi", r"bye$"),
            ),
            (
                lambda m: modify_text(m, "abcdefg"),
                fil.text.length((5, 10)),
            ),
            (
                lambda m: modify_text(m, "!start"),
                fil.text.command("start"),
            ),
            (
                lambda m: modify_text(m, "/start"),
                fil.text.command("start", prefixes="!/"),
            ),
            (
                lambda m: modify_text(m, "!Start"),
                fil.text.command("staRt", ignore_case=True),
            ),
            (
                lambda m: modify_text(m, "!start"),
                fil.text.is_command,
            ),
        ],
        "image": [
            (same, fil.image),
            (lambda m: add_caption(m), fil.image.has_caption),
            (
                lambda m: modify_img_mime_type(m, "image/jpeg"),
                fil.image.mimetypes("image/jpeg"),
            ),
        ],
        "video": [
            (same, fil.video),
            (lambda m: add_caption(m), fil.video.has_caption),
        ],
        "document": [
            (same, fil.document),
            (lambda m: add_caption(m), fil.document.has_caption),
        ],
        "audio": [
            (same, fil.audio.audio),
        ],
        "voice": [
            (same, fil.audio.voice),
        ],
        "static_sticker": [
            (same, fil.sticker.static),
        ],
        "animated_sticker": [
            (same, fil.sticker.animated),
        ],
        "reaction": [
            (same, fil.reaction.added),
            (
                lambda m: modify_reaction(m, "😀"),
                fil.reaction.emojis("😀"),
            ),
        ],
        "unreaction_empty": [
            (same, fil.reaction.removed),
        ],
        "unreaction_no_emoji": [(same, fil.reaction.removed)],
        "current_location": [
            (same, fil.location.current_location),
            (
                lambda m: modify_location(m, 37.4611794, -122.2531785),
                fil.location.in_radius(37.47, -122.25, 10),
            ),
        ],
        "chosen_location": [(same, fil.not_(fil.location.current_location))],
        "contacts": [
            (same, fil.contacts),
            (
                lambda m: add_wa_number_to_contact(m),
                fil.contacts.has_wa,
            ),
            (
                lambda m: keep_only_one_contact(m),
                fil.contacts.count(min_count=1, max_count=1),
            ),
            (
                lambda m: modify_contact_phone(m, "123456789"),
                fil.contacts.phones("+123456789"),
            ),
        ],
        "order": [
            (same, fil.order),
            (
                lambda m: modify_order_price(m, 100, 3),
                fil.order.price(min_price=100, max_price=400),
            ),
            (
                lambda m: modify_order_products_count(m, 3),
                fil.order.count(min_count=2, max_count=5),
            ),
            (
                lambda m: modify_order_product_sku(m, "SKU123"),
                fil.order.has_product("SKU123"),
            ),
        ],
        "unsupported": [(same, fil.unsupported)],
        "reply": [(same, fil.reply)],
        "forwarded": [(same, fil.forwarded)],
        "forwarded_many_times": [(same, fil.forwarded)],
        "interactive_message_with_err": [],
    },
    "callback_button": {
        "button": [
            (
                lambda m: modify_callback_data(m, "hi"),
                fil.callback.data_matches("hi"),
            ),
            (
                lambda m: modify_callback_data(m, "Hi"),
                fil.callback.data_matches("hi", ignore_case=True),
            ),
            (
                lambda m: modify_callback_data(m, "hi bye"),
                fil.callback.data_contains("hi"),
            ),
            (
                lambda m: modify_callback_data(m, "hi bye"),
                fil.callback.data_contains("Hi", ignore_case=True),
            ),
            (
                lambda m: modify_callback_data(m, "hi bye"),
                fil.callback.data_startswith("hi"),
            ),
            (
                lambda m: modify_callback_data(m, "hi bye"),
                fil.callback.data_startswith("Hi", ignore_case=True),
            ),
            (
                lambda m: modify_callback_data(m, "hi bye"),
                fil.callback.data_endswith("bye"),
            ),
            (
                lambda m: modify_callback_data(m, "hi bye"),
                fil.callback.data_endswith("Bye", ignore_case=True),
            ),
            (
                lambda m: modify_callback_data(m, "data:123"),
                fil.callback.data_regex("^data:", r"\d{3}$"),
            ),
        ],
        "quick_reply": [],
    },
    "callback_selection": {
        "callback": [],
        "description": [],
    },
    "message_status": {
        "sent": [(same, fil.message_status.sent)],
        "failed": [
            (
                lambda m: modify_status_err(
                    m, WhatsAppError.from_dict({"code": 131053, "message": "error"})
                ),
                fil.message_status.failed_with(MediaUploadError),
            ),
            (
                lambda m: modify_status_err(
                    m, WhatsAppError.from_dict({"code": 131053, "message": "error"})
                ),
                fil.message_status.failed_with(131053),
            ),
        ],
    },
    "template_status": {
        "approved": [
            (same, fil.template_status.on_event(TemplateStatus.TemplateEvent.APPROVED))
        ],
    },
    "flow_completion": {"completion": []},
}

RANDOM_API_VER = random.choice(API_VERSIONS)


def test_combinations():
    assert fil.all_(lambda _, __: True, lambda _, __: True)
    assert fil.any_(lambda _, __: True, lambda _, __: False)
    assert fil.not_(lambda _, __: False)


def test_filters():
    for filename, tests in UPDATES[RANDOM_API_VER].items():
        for test in tests:
            for test_name, update in test.items():
                for update_modifier, filter_func in FILTERS.get(filename, {}).get(
                    test_name, ()
                ):
                    update = update_modifier(update)
                    try:
                        assert filter_func(WA_NO_FILTERS, update)
                    except AssertionError as e:
                        raise AssertionError(
                            f"Test {filename}/{test_name} failed on {update}"
                        ) from e


def modify_text(msg: Message, to: str):
    return dataclasses.replace(msg, text=to)


def add_caption(msg: Message):
    return dataclasses.replace(msg, caption="Caption")


def modify_img_mime_type(msg: Message, mime_type: str):
    return dataclasses.replace(
        msg, image=dataclasses.replace(msg.image, mime_type=mime_type)
    )


def modify_reaction(msg: Message, emoji: str | None):
    return dataclasses.replace(
        msg, reaction=dataclasses.replace(msg.reaction, emoji=emoji)
    )


def modify_location(msg: Message, lat: float, lon: float):
    return dataclasses.replace(
        msg, location=dataclasses.replace(msg.location, latitude=lat, longitude=lon)
    )


def modify_contact_phone(msg: Message, phone: str):
    return dataclasses.replace(
        msg,
        contacts=(
            dataclasses.replace(
                msg.contacts[0],
                phones=[dataclasses.replace(msg.contacts[0].phones[0], phone=phone)],
            ),
        ),
    )


def add_wa_number_to_contact(msg: Message):
    return dataclasses.replace(
        msg,
        contacts=(
            dataclasses.replace(
                msg.contacts[0],
                phones=[
                    dataclasses.replace(msg.contacts[0].phones[0], wa_id="123456789")
                ],
            ),
        ),
    )


def keep_only_one_contact(msg: Message):
    return dataclasses.replace(msg, contacts=msg.contacts[:1])


def modify_order_price(msg: Message, price: int, quantity: int):
    return dataclasses.replace(
        msg,
        order=dataclasses.replace(
            msg.order,
            products=[
                dataclasses.replace(
                    msg.order.products[0], price=price, quantity=quantity
                )
            ],
        ),
    )


def modify_order_products_count(msg: Message, count: int):
    return dataclasses.replace(
        msg,
        order=dataclasses.replace(
            msg.order,
            products=[msg.order.products[0] for _ in range(count)],
        ),
    )


def modify_order_product_sku(msg: Message, sku: str):
    return dataclasses.replace(
        msg,
        order=dataclasses.replace(
            msg.order,
            products=[dataclasses.replace(msg.order.products[0], sku=sku)],
        ),
    )


def modify_callback_data(clb: CallbackButton | CallbackSelection, data: str):
    return dataclasses.replace(clb, data=data)


def modify_status_err(status: MessageStatus, err: WhatsAppError):
    return dataclasses.replace(status, error=err)
