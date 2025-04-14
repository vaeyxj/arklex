# Chat Models

## Supported Language Models
### Providers
**1\. OpenAI** (Default)
- Models: `gpt-4o` (default), `gpt-4o-mini`

**2\. Google Gemini**
- Models: ` gemini-1.5-flash`, `gemini-2.0-flash-exp`, `gemini-2.0-flash-lite`

**3\. Anthropic**
- Models: `claude-3-5-haiku-20241022`, `claude-3-haiku-20240307`

**NOTE:** Tool calling is only supported with `OpenAI` and `Anthropic` models

## Taskgraph 
- **Note:** Taskgraph construction with different models isn't supported at the time, only OpenAI can be used. Feature is planned to be implemented in the future.

## Running the Bot

### OpenAI
- Add your `OPEN_API_KEY` to the `.env` file
- Example usage:
    ```
    python run.py --input-dir ./examples/customer_service --model gpt-4o-mini --llm-provider openai
    ```
    
### Google Gemini
- Add your `GOOGLE_API_KEY`  and `GEMINI_API_KEY` to the `.env` file
    - Note: Both API keys should be the same
- Example usage:
     ```
    python run.py --input-dir ./examples/customer_service --model gemini-2.0-flash-lite --llm-provider gemini
    ```

### Anthropic
- Add your `ANTHROPIC_API_KEY` to the `.env` file
- Example usage:
    ```
    python run.py --input-dir ./examples/customer_service --model claude-3-5-haiku-20241022 --llm-provider anthropic
    ```



## Sample conversation
To run the bot, use the following command:
  ```
python run.py --input-dir ./examples/customer_service --model claude-3-5-haiku-20241022 --llm-provider anthropic
  ```

### Example Output

> **ASSISTANT**: Hello! I'm your Customer Service Assistant. How can I assist you with your inquiries today? Whether you need information about our products, services, or policies, or require help resolving an issue, I'm here to help!
> 
> **USER**:  What products do you offer?
>
> **ASSISTANT**: At Richtech Robotics, we offer a range of advanced business-oriented robots across several categories:
>
> Worker Robots:
> - ADAM (multipurpose robot bartender for making tea, coffee, and cocktails)
> - ARM
> - ACE
>
> Delivery Robots:
> - Matradee
> - Matradee X
> - Matradee L
> - Richie
>
> Cleaning Robots:
> - DUST-E SX
> - DUST-E MX
>
> Multipurpose Robots:
> - Skylark
>
> Our robots are designed for business applications, not home use. The ADAM robot is particularly unique, as it's available for both purchase and rental, and we even operate the world's first robot milk tea shop, ClouTea, in Las Vegas using this robot.
>
 >Can you please provide more details about the robot you are interested in, such as the model name or specific features you are curious about?'
>
> **USER**: Tell me more about the worker robots, what are their differences?
>
> **ASSISTANT**:
>Let me provide you with details about our worker robots:
>
>ADAM Robot:
> - Multipurpose bartending robot
> - Can prepare tea, coffee, and cocktails
> - Available for purchase and rental
> - Featured in our ClouTea milk tea shop in Las Vegas
> - Typical delivery time: 2 weeks
>
> ARM Robot:
> - Specialized worker robot
> - Specific details would require further consultation
> - Used in various industrial and business settings
>
> ACE Robot:
> - Another worker robot in our lineup
> - Designed for specific industrial applications
> - Detailed specifications would need a more in-depth discussion
>
> Do you need any further information or have additional questions about the robot?
>
> Each of these robots has unique capabilities tailored to different business needs. Would you like me to elaborate on any specific features or help you determine which robot might best suit your requirements?'
>
> **USER**: I'm interested in ADAM, can we book a demo?
>
> **ASSISTANT**: Absolutely! I can help you book a demo for our ADAM robot. We offer several ways to schedule a demonstration:
>
> 1. Online Booking: You can visit our robot rentals page at
 https://www.richtechrobotics.com/robot-rentals#rent-new-form to schedule a demo.
>
> 2. Contact Our Sales Team: You can reach our sales line at (866) 236-3835 to discuss a demo and explore how ADAM can benefit your business.
>
>To proceed with booking a demo, I'll need a bit more information from you:
> - What is your name?
> - What is your company name?
> - What is the best contact number and email address to reach you?
> - Are you interested in a demo for an event, business use, or general exploration?
>
> Once I have these details, I can help guide you through the demo scheduling process and connect you with our sales team who can provide more specific information about the ADAM robot's capabilities.

