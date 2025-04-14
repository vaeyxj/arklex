import json
from typing import Any, Dict
import shopify
import logging

# general GraphQL navigation utilities
from arklex.env.tools.shopify.utils_slots import ShopifySearchProductsSlots, ShopifyOutputs
from arklex.env.tools.shopify.utils_nav import *
from arklex.env.tools.shopify.utils import authorify_admin

# Admin API
from arklex.env.tools.tools import register_tool

from arklex.utils.model_provider_config import PROVIDER_MAP
from arklex.utils.model_config import MODEL
from langchain_deepseek import ChatDeepSeek


logger = logging.getLogger(__name__)


description = "Search products by string query. If no products are found, the function will return an error message."
slots = ShopifySearchProductsSlots.get_all_slots()
outputs = [
    ShopifyOutputs.PRODUCT_ID,
    *PAGEINFO_OUTPUTS
]
PRODUCT_SEARCH_ERROR = "error: product search failed"
NO_PRODUCTS_FOUND_ERROR = "no products found"

errors = [
    PRODUCT_SEARCH_ERROR,
    NO_PRODUCTS_FOUND_ERROR,
    NAVIGATE_WITH_NO_CURSOR,
    NO_NEXT_PAGE,
    NO_PREV_PAGE
]

@register_tool(description, slots, outputs, lambda x: x[0] not in errors, True)
def search_products(product_query: str, **kwargs) -> str:
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
                    products ({nav[0]}, query: "{product_query}") {{
                        nodes {{
                            id
                            title
                            description
                            onlineStoreUrl
                            images(first: 1) {{
                                edges {{
                                    node {{
                                        src
                                        altText
                                    }}
                                }}
                            }}
                            variants (first: 3) {{
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
            answer = "Here are some products I found:\n"
            products = json.loads(response)['data']['products']['nodes']
            card_list = []
            for product in products:
                product_dict = {
                    "id": product.get('id'),
                    "title": product.get('title'),
                    "description": product.get('description', "None")[:180] + "...",
                    "link_url": product.get('onlineStoreUrl'),
                    "image_url": product.get('images', {}).get('edges', [{}])[0].get('node', {}).get('src', ""), 
                    "variants": product.get('variants', {}).get('nodes', [])
                }
                card_list.append(product_dict)
            if card_list:
                try:
                    llm = PROVIDER_MAP.get(MODEL['llm_provider'], ChatDeepSeek)(model=MODEL["model_type_or_path"], timeout=30000)
                    message = [
                        {"role": "system", "content": f"You are helping a customer search products based on the query and get results below and those results will be presented using product card format.\n\n{json.dumps(card_list)}\n\nGenerate a response to continue the conversation without explicitly mentioning contents of the search result. Include one or two questions about those products to know the user's preference. Keep the response within 50 words.\nDIRECTLY GIVE THE RESPONSE."},
                    ]
                    answer = llm.invoke(message).content
                except Exception as e:
                    logger.info(f"llm error in search_products: {e}")
                    pass
                return json.dumps({
                    "answer": answer,
                    "card_list": card_list
                })
            else:
                return json.dumps({
                    "answer": NO_PRODUCTS_FOUND_ERROR,
                    "card_list": []
                })
    
    except Exception as e:
        return json.dumps({
            "answer": NO_PRODUCTS_FOUND_ERROR,
            "card_list": []
        })