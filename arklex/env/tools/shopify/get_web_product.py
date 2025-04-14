import json
from typing import Any, Dict
import logging

import shopify

# general GraphQL navigation utilities
from arklex.env.tools.shopify.utils_nav import *
from arklex.env.tools.shopify.utils import authorify_admin

# ADMIN
from arklex.env.tools.shopify.utils_slots import ShopifyGetWebProductSlots, ShopifyOutputs
from arklex.env.tools.tools import register_tool

logger = logging.getLogger(__name__)

description = "Get the inventory information and description details of a product."
slots = ShopifyGetWebProductSlots.get_all_slots()
outputs = [
    ShopifyOutputs.PRODUCTS_DETAILS,
    *PAGEINFO_OUTPUTS
]
PRODUCT_NOT_FOUND = "error: product not found"
errors = [PRODUCT_NOT_FOUND]

@register_tool(description, slots, outputs, lambda x: x not in errors)
def get_web_product(web_product_id: str, **kwargs) -> str:
    nav = cursorify(kwargs)
    if not nav[1]:
        return nav[0]
    auth = authorify_admin(kwargs)
    if auth["error"]:
        return auth["error"]

    try:
        with shopify.Session.temp(**auth["value"]):
            response = shopify.GraphQL().execute(f"""
                {{
                    products ({nav[0]}, query:"id:{web_product_id.split("/")[-1]}") {{
                        nodes {{
                            id
                            title
                            description
                            totalInventory
                            onlineStoreUrl
                            options {{
                                name
                                values
                            }}
                            category {{
                                name
                            }}
                            variants (first: 2) {{
                                nodes {{
                                    displayName
                                    id
                                    price
                                    inventoryQuantity
                                }}
                            }}
                        }}
                        pageInfo {{
                            endCursor
                            hasNextPage
                            hasPreviousPage
                            startCursor
                        }}
                    }}
                }}
            """)
            result = json.loads(response)['data']['products']
            response = result["nodes"]
            if len(response) == 0:
                return PRODUCT_NOT_FOUND
            product = response[0]
            response_text = ""
            response_text += f"Product ID: {product.get('id', 'None')}\n"
            response_text += f"Title: {product.get('title', 'None')}\n"
            response_text += f"Description: {product.get('description', 'None')}\n"
            response_text += f"Total Inventory: {product.get('totalInventory', 'None')}\n"
            response_text += f"Options: {product.get('options', 'None')}\n"
            response_text += f"Category: {product.get('category', {}.get('name', 'None'))}\n"
            response_text += "The following are several variants of the product:\n"
            for variant in product.get('variants', {}).get('nodes', []):
                response_text += f"Variant name: {variant.get('displayName', 'None')}, Variant ID: {variant.get('id', 'None')}, Price: {variant.get('price', 'None')}, Inventory Quantity: {variant.get('inventoryQuantity', 'None')}\n"
            response_text += "\n"

            return response_text
    except Exception as e:
        return PRODUCT_NOT_FOUND
