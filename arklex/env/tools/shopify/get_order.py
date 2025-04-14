"""
This module is currently inactive.

It is reserved for future use and may contain experimental or planned features (dependence on refresh token).

Status:
    - Not in use (as of 2025-02-18)
    - Intended for future feature expansion

Module Name: get_order

This file contains the code for getting the status and details of an order.
"""
from typing import Any, Dict

from arklex.env.tools.tools import register_tool

# general GraphQL navigation utilities
from arklex.env.tools.shopify.utils_nav import *

# Customer API
from arklex.env.tools.shopify.utils_slots import ShopifySlots, ShopifyOutputs
from arklex.env.tools.shopify.utils import *
from arklex.env.tools.shopify.auth_utils import *

description = "Get the status and details of an order."
slots = [
    ShopifySlots.REFRESH_TOKEN,
    ShopifySlots.ORDER_ID,
    *PAGEINFO_SLOTS
]
outputs = [
    ShopifyOutputs.ORDERS_DETAILS,
    *PAGEINFO_OUTPUTS
]

ORDERS_NOT_FOUND = "error: order not found"
errors = [ORDERS_NOT_FOUND]

@register_tool(description, slots, outputs, lambda x: x not in errors)
def get_order(refresh_token, order_id: str, **kwargs) -> str:
    nav = cursorify(kwargs)
    if not nav[1]: 
        return nav[0]
    
    try:
        body = f'''
            query {{ 
                order (id: "{order_id}") {{ 
                    id
                    name
                    totalPrice {{
                        amount
                    }}
                    lineItems({nav[0]}) {{
                        nodes {{
                            id
                            name
                            quantity
                        }}
                        pageInfo {{
                            endCursor
                            hasNextPage
                            hasPreviousPage
                            startCursor
                        }}
                    }}
                }} 
            }}
        '''
        try:
            auth = {'Authorization': get_access_token(refresh_token)}
        except:
            return AUTH_ERROR
        
        try:
            response = make_query(customer_url, body, {}, customer_headers | auth)['data']['order']
        except Exception as e:
            return f"error: {e}"
        
        pageInfo = response['lineItems']['pageInfo']
        return response, pageInfo
    except Exception as e:
        return ORDERS_NOT_FOUND
