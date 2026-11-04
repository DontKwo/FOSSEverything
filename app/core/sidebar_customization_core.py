from dataclasses import dataclass, field
from typing import Any
from app.core.home_apps import HOME_APPS, HOME_CATEGORIES


@dataclass
class SidebarItem:
    id: str
    visible: bool = True


@dataclass
class SidebarSection:
    id: str
    name: str
    collapsed: bool = False
    items: list[SidebarItem] = field(default_factory=list)


@dataclass
class SidebarLayout:
    version: int = 1
    sections: list[SidebarSection] = field(default_factory=list)


def serialize_sidebar_layout(layout: SidebarLayout) -> dict[str, Any]:
    return {
        "version": layout.version,
        "sections": [
            {
                "id": sec.id,
                "name": sec.name,
                "collapsed": sec.collapsed,
                "items": [
                    {"id": item.id, "visible": item.visible} for item in sec.items
                ],
            }
            for sec in layout.sections
        ],
    }


def reset_to_defaults() -> SidebarLayout:
    sections = []

    for category in HOME_CATEGORIES:
        sec_id = f"sec_{category.lower().replace(' ', '_')}"
        section = SidebarSection(id=sec_id, name=category)

        for app in HOME_APPS:
            if app.category == category:
                section.items.append(SidebarItem(id=app.id, visible=True))

        sections.append(section)

    return SidebarLayout(version=1, sections=sections)


def deserialize_sidebar_layout(data: dict[str, Any] | None) -> SidebarLayout:
    if not data or not isinstance(data, dict):
        return reset_to_defaults()

    version = data.get("version")
    if version != 1:
        return reset_to_defaults()

    sections_data = data.get("sections")
    if not isinstance(sections_data, list):
        return reset_to_defaults()

    layout = SidebarLayout(version=1)

    for sec_data in sections_data:
        if not isinstance(sec_data, dict):
            continue

        sec = SidebarSection(
            id=sec_data.get("id", ""),
            name=sec_data.get("name", ""),
            collapsed=sec_data.get("collapsed", False),
        )

        items_data = sec_data.get("items", [])
        if isinstance(items_data, list):
            for item_data in items_data:
                if isinstance(item_data, dict):
                    sec.items.append(
                        SidebarItem(
                            id=item_data.get("id", ""),
                            visible=item_data.get("visible", True),
                        )
                    )

        layout.sections.append(sec)

    return layout
