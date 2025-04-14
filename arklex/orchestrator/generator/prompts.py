generate_tasks_sys_prompt = """The builder plans to create a chatbot designed to fulfill user's objectives. Given the role of the chatbot, along with any introductory information and detailed documentation (if available), your task is to identify the specific, distinct tasks that a chatbot should handle based on the user's intent. These tasks should not overlap or depend on each other and must address different aspects of the user's goals. Ensure that each task represents a unique user intent and that they can operate separately. Return the response in JSON format.

For Example:

Builder's prompt: The builder want to create a chatbot - Customer Service Assistant. The customer service assistant typically handles tasks such as answering customer inquiries, making product recommendations, assisting with orders, processing returns and exchanges, supporting billing and payments, addressing complaints, and managing customer accounts.
Builder's Information: Amazon.com is a large e-commerce platform that sells a wide variety of products, ranging from electronics to groceries.
Builder's documentations: 
https://www.amazon.com/
Holiday Deals
Disability Customer Support
Same-Day Delivery
Medical Care
Customer Service
Amazon Basics
Groceries
Prime
Buy Again
New Releases
Pharmacy
Shop By Interest
Amazon Home
Amazon Business
Subscribe & Save
Livestreams
luwanamazon's Amazon.com
Best Sellers
Household, Health & Baby Care
Sell
Gift Cards

https://www.amazon.com/bestsellers
Any Department
Amazon Devices & Accessories
Amazon Renewed
Appliances
Apps & Games
Arts, Crafts & Sewing
Audible Books & Originals
Automotive
Baby
Beauty & Personal Care
Books
Camera & Photo Products
CDs & Vinyl
Cell Phones & Accessories
Clothing, Shoes & Jewelry
Collectible Coins
Computers & Accessories
Digital Educational Resources
Digital Music
Electronics
Entertainment Collectibles
Gift Cards
Grocery & Gourmet Food
Handmade Products
Health & Household
Home & Kitchen
Industrial & Scientific
Kindle Store
Kitchen & Dining
Movies & TV
Musical Instruments
Office Products
Patio, Lawn & Garden
Pet Supplies
Software
Sports & Outdoors
Sports Collectibles
Tools & Home Improvement
Toys & Games
Unique Finds
Video Games

Reasoning Process:
Thought 1: Understand the general responsibilities of the assistant type.
Observation 1: A customer service assistant typically handles tasks such as answering customer inquiries, addressing complaints, making product recommendations, assisting with orders, processing returns and exchanges, supporting billing and payments, and managing customer accounts.

Thought 2: Based on these general tasks, identify the specific tasks relevant to this assistant, taking into account the customer's decision-making journey. Consider the typical activities customers engage in on this platform and the potential questions they might ask.
Observation 2: The customer decision-making journey includes stages like need recognition, information search, evaluating alternatives, making a purchase decision, and post-purchase behavior. On Amazon, customers log in, browse and compare products, add items to their cart, and check out. They also track orders, manage returns, and leave reviews. Therefore, the assistant would handle tasks such as product search and discovery, product inquiries, product comparison, billing and payment support, order management, and returns and exchanges.

Thought 3: Summarize the identified tasks in terms of user intent and format them into JSON.
Observation 3: Structure the output as a list of dictionaries, where each dictionary represents an intent and its corresponding task.

Answer:
```json
[
    {{
        "intent": "User want to do product search and discovery",
        "task": "Provide help in Product Search and Discovery"
    }},
    {{
        "intent": "User has product inquiry",
        "task": "Provide help in product inquiry"
    }},
    {{
        "intent": "User want to compare different products",
        "task": "Provide help in product comparison"
    }},
    {{
        "intent": "User ask for billing and payment support",
        "task": "Provide help in billing and payment support"
    }},
    {{
        "intent": "User want to manage orders",
        "task": "Provide help in order management"
    }},
    {{
        "intent": "User has request in returns and exchanges",
        "task": "Provide help in Returns and Exchanges"
    }}
]
```

Builder's prompt: The builder want to create a chatbot - {role}. {u_objective}
Builder's information: {intro}
Builder's documentations: 
{docs}
Reasoning Process:
"""


check_best_practice_sys_prompt = """You are a userful assistance to detect if the current task needs to be further decomposed if it cannot be solved by the provided resources. Specifically, the task is positioned on a tree structure and is associated with a level. Based on the task and the current node level of the task on the tree, please output Yes if it needs to be decomposed; No otherwise meaning it is a singular task that can be handled by the resource and does not require task decomposition. Please also provide explanations for your choice. 

Here are some examples:
Task: The current task is Provide help in Product Search and Discovery. The current node level of the task is 1. 
Resources: 
MessageWorker: The worker responsible for interacting with the user with predefined responses,
RAGWorker: Answer the user's questions based on the company's internal documentations, such as the policies, FAQs, and product information,
ProductWorker: Access the company's database to retrieve information about products, such as availability, pricing, and specifications,
UserProfileWorker: Access the company's database to retrieve information about the user's preferences and history

Reasoning: This task is a high-level task that involves multiple sub-tasks such as asking for user's preference, providing product recommendations, answering questions about product or policy, and confirming user selections. Each sub-task requires different worker to complete. It will use MessageWorker to ask user's preference, then use ProductWorker to search for the product, finally make use of RAGWorker to answer user's question. So, it requires multiple interactions with the user and access to various resources. Therefore, it needs to be decomposed into smaller sub-tasks to be effectively handled by the assistant.
Answer: 
```json
{{
    "answer": "Yes"
}}
```

Task: The current task is booking a broadway show ticket. The current node level of the task is 1.
Resources:
DataBaseWorker: Access the company's database to retrieve information about ticket availability, pricing, and seating options. It will handle the booking process, which including confirming the booking details and providing relevant information. It can also handle the cancel process.
MessageWorker: The worker responsible for interacting with the user with predefined responses,
RAGWorker: Answer the user's questions based on the company's internal documentations, such as the policies, FAQs, and product information.

Reasoning: This task involves a single high-level action of booking a ticket for a broadway show. The task can be completed by accessing the database to check availability, pricing, and seating options, interacting with the user to confirm the booking details, and providing relevant information. Since it is a singular task that can be handled by the single resource without further decomposition, the answer is No.
Answer: 
```json
{{
    "answer": "No"
}}
```

Task: The current task is {task}. The current node level of the task is {level}.
Resources: {resources}
Reasoning:
"""


generate_best_practice_sys_prompt = """Given the background information about the chatbot, the task it needs to handle, and the available resources, your task is to generate a step-by-step best practice for addressing this task. Each step should represent a distinct interaction with the user, where the next step builds upon the user's response. Avoid breaking down sequences of internal worker actions within a single turn into multiple steps. Return the answer in JSON format. Only use resources listed in the input, resources listed in the Example may not be available.

For example:
Background: The builder want to create a chatbot - Customer Service Assistant. The customer service assistant typically handles tasks such as answering customer inquiries, making product recommendations, assisting with orders, processing returns and exchanges, supporting billing and payments, addressing complaints, and managing customer accounts.

Task: Provide help in Product Search and Discovery

Resources:
MessageWorker: The worker responsible for interacting with the user with predefined responses,
RAGWorker: Answer the user's questions based on the company's internal documentations, such as the policies, FAQs, and product information,
ProductWorker: Access the company's database to retrieve information about products, such as availability, pricing, and specifications,
UserProfileWorker: Access the company's database to retrieve information about the user's preferences and history.

Thought: To help users find products effectively, the assistant should first get context information about the customer from CRM, such as purchase history, demographic information, preference metadata, inquire about specific preferences or requirements (e.g., brand, features, price range) specific for the request. Second, based on the user's input, the assistant should provide personalized product recommendations. Third, the assistant should ask if there is anything not meet their goals. Finally, the assistant should confirm the user's selection, provide additional information if needed, and assist with adding the product to the cart or wish list.
Answer:
```json
[
    {{
      "step": 1,
      "task": "Retrieve the information about the customer and Inquire about specific preferences or requirements (e.g., brand, features, price range)."
    }},
    {{
      "step": 2,
      "task": "Search for the products that match user's preference and provide a curated list of products that match the user's criteria."
    }},
    {{
      "step": 3,
      "task": "Ask if the user would like to see more options or has any specific preferences."
    }},
    {{
      "step": 4,
      "task": "Confirm if the user is ready to proceed with a purchase or needs more help."
    }},
    {{
      "step": 5,
      "task": "Provide instructions for completing the purchase or next steps."
    }}
]
```

Background: The builder want to create a chatbot - {role}. {u_objective}
Task: {task}
Resources: {resources}
Thought:
"""


# remove_duplicates_sys_prompt = """The builder plans to create a chatbot designed to fulfill user's objectives. Given the tasks and corresponding steps that the chatbot should handle, your task is to identify and remove any duplicate steps under each task that are already covered by other tasks. Ensure that each step is unique within the overall set of tasks and is not redundantly assigned. Return the response in JSON format.

# Tasks: {tasks}
# Answer:
# """

embed_builder_obj_sys_prompt = """The builder plans to create an assistant designed to provide services to users. Given the best practices for addressing a specific task and the builder's objectives, your task is to refine the steps to ensure they embed the objectives within each task. Return the answer in JSON format.

For example:
Best Practice: 
[
    {{
        "step": 1,
        "task": "Retrieve the information about the customer and Inquire about specific preferences or requirements (e.g., brand, features, price range)."
    }},
    {{
        "step": 2,
        "task": "Provide a curated list of products that match the user's criteria."
    }},
    {{
        "step": 3,
        "task": "Ask if the user would like to see more options or has any specific preferences."
    }},
    {{
        "step": 4,
        "task": "Confirm if the user is ready to proceed with a purchase or needs more help."
    }},
    {{
        "step": 5,
        "task": "Provide instructions for completing the purchase or next steps."
    }}
]
Build's objective: The customer service assistant helps in persuading customer to sign up the Prime membership.
Answer:
```json
[
    {{
        "step": 1,
        "task": "Retrieve the information about the customer from CRM and Inquire about specific preferences or requirements (e.g., brand, features, price range)."
    }},
    {{
        "step": 2,
        "task": "Provide a curated list of products that match the user's criteria."
    }},
    {{
        "step": 3,
        "task": "Ask if the user would like to see more options or has any specific preferences."
    }},
    {{
        "step": 4,
        "task": "Confirm if the user is ready to proceed with a purchase or needs more help."
    }},
    {{
        "step": 5,
        "task": "Persuade the user to sign up for the Prime membership."
    }}
]
```

Best Practice: {best_practice}
Build's objective: {b_objective}
Answer:
"""


embed_resources_sys_prompt = """The builder plans to create an assistant designed to provide services to users. Given the best practices for addressing a specific task, and the available resources, your task is to map the steps with the resources. The response should include the resources used for each step and example responses, if applicable. Return the answer in JSON format. Do not add any comment on the answer.

For example:
Best Practice: 
[
    {{
        "step": 1,
        "task": "Retrieve the information about the customer from CRM and Inquire about specific preferences or requirements (e.g., brand, features, price range)."
    }},
    {{
        "step": 2,
        "task": "Provide a curated list of products that match the user's criteria."
    }},
    {{
        "step": 3,
        "task": "Ask if the user would like to see more options or has any specific preferences."
    }},
    {{
        "step": 4,
        "task": "Confirm if the user is ready to proceed with a purchase or needs more help."
    }},
    {{
        "step": 5,
        "task": "Persuade the user to sign up for the Prime membership."
    }}
]
Resources:
{{
    "MessageWorker": "The worker responsible for interacting with the user with predefined responses",
    "RAGWorker": "Answer the user's questions based on the company's internal documentations, such as the policies, FAQs, and product information",
    "ProductWorker": "Access the company's database to retrieve information about products, such as availability, pricing, and specifications",
    "UserProfileWorker": "Access the company's database to retrieve information about the user's preferences and history"
}}
Answer:
```json
[
    {{
        "step": 1,
        "task": "Retrieve the information about the customer from CRM and Inquire about specific preferences or requirements (e.g., brand, features, price range)."
        "resource": "UserProfileWorker",
        "example_response": "Do you have some specific preferences or requirements for the product you are looking for?"
    }},
    {{
        "step": 2,
        "task": "Provide a curated list of products that match the user's criteria."
        "resource": "ProductWorker",
        "example_response": ""
    }},
    {{
        "step": 3,
        "task": "Ask if the user would like to see more options or has any specific preferences."
        "resource": "MessageWorker",
        "example_response": "Would you like to see more options or do you have any specific preferences?"
    }},
    {{
        "step": 4,
        "task": "Confirm if the user is ready to proceed with a purchase or needs more help."
        "resource": "MessageWorker",
        "example_response": "Are you ready to proceed with the purchase or do you need more help?"
    }},
    {{
        "step": 5,
        "task": "Persuade the user to sign up for the Prime membership."
        "resource": "MessageWorker",
        "example_response": "I noticed that you are a frequent shopper. Have you considered signing up for our Prime membership to enjoy exclusive benefits and discounts?"
    }}
]
```

Best Practice: {best_practice}
Resources: {resources}
Answer:
"""


generate_start_msg = """The builder plans to create a chatbot designed to fulfill user's objectives. Given the role of the chatbot, your task is to generate a starting message for the chatbot. Return the response in JSON format.

For Example:

Builder's prompt: The builder want to create a chatbot - Customer Service Assistant. The customer service assistant typically handles tasks such as answering customer inquiries, making product recommendations, assisting with orders, processing returns and exchanges, supporting billing and payments, addressing complaints, and managing customer accounts.
Start Message:
```json
{{
    "message": "Welcome to our Customer Service Assistant! How can I help you today?"
}}
```

Builder's prompt: The builder want to create a chatbot - {role}. {u_objective}
Start Message:
"""