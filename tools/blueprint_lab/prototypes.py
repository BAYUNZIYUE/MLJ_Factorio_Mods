from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Ingredient:
    name: str
    amount: float
    type: str = "item"


@dataclass(frozen=True)
class Product:
    name: str
    amount: float
    type: str = "item"
    probability: float = 1.0


@dataclass(frozen=True)
class Recipe:
    name: str
    category: str
    energy_required: float
    ingredients: list[Ingredient]
    products: list[Product]
    main_product: str | None = None


@dataclass(frozen=True)
class CraftingEntity:
    name: str
    type: str
    crafting_categories: list[str]
    crafting_speed: float
    module_slots: int


@dataclass(frozen=True)
class PrototypeKnowledge:
    recipes: dict[str, Recipe]
    crafting_entities: dict[str, CraftingEntity]

    def recipe(self, name: str) -> Recipe | None:
        return self.recipes.get(name)

    def entity(self, name: str) -> CraftingEntity | None:
        return self.crafting_entities.get(name)


def value_amount(value: Any, default: float = 1.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def normalize_ingredient(value: Any) -> Ingredient | None:
    if isinstance(value, list) and value:
        name = str(value[0])
        amount = value_amount(value[1], 1.0) if len(value) > 1 else 1.0
        return Ingredient(name=name, amount=amount)
    if isinstance(value, dict):
        name = value.get("name") or value.get(1)
        if not name:
            return None
        return Ingredient(
            name=str(name),
            amount=value_amount(value.get("amount") or value.get("amount_min") or value.get("amount_max"), 1.0),
            type=str(value.get("type") or "item"),
        )
    return None


def normalize_product(value: Any) -> Product | None:
    if isinstance(value, list) and value:
        name = str(value[0])
        amount = value_amount(value[1], 1.0) if len(value) > 1 else 1.0
        return Product(name=name, amount=amount)
    if isinstance(value, dict):
        name = value.get("name") or value.get(1)
        if not name:
            return None
        amount = value.get("amount")
        if amount is None:
            amount_min = value.get("amount_min")
            amount_max = value.get("amount_max")
            if isinstance(amount_min, (int, float)) and isinstance(amount_max, (int, float)):
                amount = (float(amount_min) + float(amount_max)) / 2
        return Product(
            name=str(name),
            amount=value_amount(amount, 1.0),
            type=str(value.get("type") or "item"),
            probability=value_amount(value.get("probability"), 1.0),
        )
    return None


def recipe_body(proto: dict[str, Any]) -> dict[str, Any]:
    normal = proto.get("normal")
    if isinstance(normal, dict):
        merged = dict(proto)
        merged.update(normal)
        return merged
    return proto


def normalize_recipe(name: str, proto: dict[str, Any]) -> Recipe:
    body = recipe_body(proto)
    ingredients = [
        item
        for value in body.get("ingredients") or []
        if (item := normalize_ingredient(value)) is not None
    ]
    products = [
        item
        for value in body.get("results") or []
        if (item := normalize_product(value)) is not None
    ]
    if not products and body.get("result"):
        products = [Product(name=str(body["result"]), amount=value_amount(body.get("result_count"), 1.0))]

    return Recipe(
        name=name,
        category=str(body.get("category") or "crafting"),
        energy_required=value_amount(body.get("energy_required"), 0.5),
        ingredients=ingredients,
        products=products,
        main_product=str(body["main_product"]) if body.get("main_product") else None,
    )


def normalize_crafting_entity(name: str, entity_type: str, proto: dict[str, Any]) -> CraftingEntity | None:
    categories = proto.get("crafting_categories") or proto.get("resource_categories")
    if not isinstance(categories, list):
        return None
    return CraftingEntity(
        name=name,
        type=entity_type,
        crafting_categories=[str(item) for item in categories],
        crafting_speed=value_amount(proto.get("crafting_speed") or proto.get("mining_speed"), 1.0),
        module_slots=int((proto.get("module_slots") or 0)),
    )


def load_data_raw(path: Path) -> PrototypeKnowledge:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(raw, dict):
        raise ValueError("data.raw JSON must be an object")

    recipe_table = raw.get("recipe") or {}
    recipes = {
        name: normalize_recipe(name, proto)
        for name, proto in recipe_table.items()
        if isinstance(proto, dict)
    }

    crafting_entities: dict[str, CraftingEntity] = {}
    for entity_type, table in raw.items():
        if not isinstance(table, dict):
            continue
        for name, proto in table.items():
            if not isinstance(proto, dict):
                continue
            entity = normalize_crafting_entity(name, entity_type, proto)
            if entity is not None:
                crafting_entities[name] = entity

    return PrototypeKnowledge(recipes=recipes, crafting_entities=crafting_entities)


def empty_knowledge() -> PrototypeKnowledge:
    return PrototypeKnowledge(recipes={}, crafting_entities={})


def render_recipe(recipe: Recipe) -> str:
    ingredients = ", ".join(f"{item.name}:{item.amount:g}" for item in recipe.ingredients) or "none"
    products = ", ".join(f"{item.name}:{item.amount:g}" for item in recipe.products) or "none"
    return (
        f"{recipe.name}: category={recipe.category} time={recipe.energy_required:g} "
        f"ingredients=[{ingredients}] products=[{products}]"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect a Factorio data.raw JSON export.")
    parser.add_argument("data_raw_json", type=Path)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args(argv)

    knowledge = load_data_raw(args.data_raw_json)
    payload = {
        "recipe_count": len(knowledge.recipes),
        "crafting_entity_count": len(knowledge.crafting_entities),
        "sample_recipes": [asdict(recipe) for recipe in list(knowledge.recipes.values())[:20]],
        "sample_crafting_entities": [asdict(entity) for entity in list(knowledge.crafting_entities.values())[:20]],
    }
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"recipes={payload['recipe_count']} crafting_entities={payload['crafting_entity_count']}")
    for recipe in list(knowledge.recipes.values())[:10]:
        print(render_recipe(recipe))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

