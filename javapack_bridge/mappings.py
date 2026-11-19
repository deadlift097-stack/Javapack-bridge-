"""Java -> Bedrock texture name tables.

Names not listed here pass through unchanged, which is correct for the many
textures whose names already match (stone, dirt, bedrock, coal_ore, ...).
Extend these tables with pull requests; every entry is Java name -> Bedrock name.
"""

COLORS = {
    "white": "white", "orange": "orange", "magenta": "magenta",
    "light_blue": "light_blue", "yellow": "yellow", "lime": "lime",
    "pink": "pink", "gray": "gray", "light_gray": "silver", "cyan": "cyan",
    "purple": "purple", "blue": "blue", "brown": "brown", "green": "green",
    "red": "red", "black": "black",
}

WOODS = {"oak": "oak", "spruce": "spruce", "birch": "birch",
         "jungle": "jungle", "acacia": "acacia", "dark_oak": "big_oak"}

BLOCKS = {
    "grass_block_top": "grass_top",
    "grass_block_side": "grass_side",
    "grass_block_snow": "grass_side_snowed",
    "bricks": "brick",
    "stone_bricks": "stonebrick",
    "mossy_stone_bricks": "stonebrick_mossy",
    "cracked_stone_bricks": "stonebrick_cracked",
    "furnace_front": "furnace_front_off",
    "furnace_front_on": "furnace_front_lit",
    "sandstone": "sandstone_normal",
    "terracotta": "hardened_clay",
    "oak_sapling": "sapling_oak",
    "spruce_sapling": "sapling_spruce",
    "birch_sapling": "sapling_birch",
    "jungle_sapling": "sapling_jungle",
    "acacia_sapling": "sapling_acacia",
    "dark_oak_sapling": "sapling_roofed_oak",
}
for java, bed in WOODS.items():
    BLOCKS[f"{java}_planks"] = f"planks_{bed}"
    BLOCKS[f"{java}_log"] = f"log_{bed}"
    BLOCKS[f"{java}_log_top"] = f"log_{bed}_top"
    BLOCKS[f"{java}_leaves"] = f"leaves_{bed}"
for java, bed in COLORS.items():
    BLOCKS[f"{java}_wool"] = f"wool_colored_{bed}"
    BLOCKS[f"{java}_terracotta"] = f"hardened_clay_stained_{bed}"
    BLOCKS[f"{java}_concrete"] = f"concrete_{bed}"
    BLOCKS[f"{java}_concrete_powder"] = f"concrete_powder_{bed}"
    BLOCKS[f"{java}_stained_glass"] = f"glass_{bed}"

ITEMS = {
    "wooden_sword": "wood_sword", "wooden_pickaxe": "wood_pickaxe",
    "wooden_axe": "wood_axe", "wooden_shovel": "wood_shovel",
    "wooden_hoe": "wood_hoe",
    "golden_sword": "gold_sword", "golden_pickaxe": "gold_pickaxe",
    "golden_axe": "gold_axe", "golden_shovel": "gold_shovel",
    "golden_hoe": "gold_hoe", "golden_apple": "apple_golden",
    "golden_helmet": "gold_helmet", "golden_chestplate": "gold_chestplate",
    "golden_leggings": "gold_leggings", "golden_boots": "gold_boots",
    "clock": "clock_item", "compass": "compass_item",
}

# Java texture folder -> (Bedrock folder, atlas kind or None)
FOLDERS = {
    "block": ("textures/blocks", "terrain"),
    "item": ("textures/items", "items"),
    "entity": ("textures/entity", None),
    "environment": ("textures/environment", None),
    "colormap": ("textures/colormap", None),
    "particle": ("textures/particle", None),
    "painting": ("textures/painting", None),
    "models/armor": ("textures/models/armor", None),
}
