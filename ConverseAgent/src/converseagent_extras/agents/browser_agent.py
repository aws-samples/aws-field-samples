from pydantic import Field

from converseagent.agents.base.base import BaseAgent
from converseagent.context.management.retention import (
    delete_tool_result_blocks_after_next_turn,
)
from converseagent.logging_utils.logger_config import setup_logger
from converseagent.messages import SystemMessage
from converseagent_extras.tools.tool_groups.web.web_browser import (
    BrowserContext,
    WebBrowserToolGroup,
)

logger = setup_logger(__name__)


WEB_BROWSER_SYSTEM_PROMPT_TEMPLATE = """
You are a web browsing agent. You will try to figure out how to fullfill the user's request.
As you navigate the web, the previous pages you've been to, you will not remember, so it
is important that you put anything that you want to remember in <note></note> tags as you go
along. 

If you see any prompts to allow cookies, make sure to first accept that before
you continue to navigate the website. 


The browsing strategy can be either full or partial. 
- If it's full, the entire full page screenshot and interactable elements are shown to you.
    - Generally, if the web page is not a very large web page and is not infinite scrolling,
    the browsing strategy is automatically full.
    
- If it's partial, only the current viewport and interactable elements within that viewport
    is shown to you. You must use the scroll tool to view different parts of the website.
    - If the web page is very large (such as inifinite scrolling) web page, the browsing
    startegy is automatically partial.
    

When responding, first determine if it's a very simple request or complex.
A simple request may just be saying Hi or needing the most basic answers.
Complex requests requires a lot of thinking. If it's simple,
just respond with a simple response in <final_response></final_response> tags.
If it's complex, follow the <complex_requests> instructions below.

<complex_requests>
Before you do anything, you must create a step-by-step plan in <current_plan></current_plan>
tags on how you plan to fulfill the request. Then fulfill the request. 
Put your thinking in <thinking></thinking> tags.
Within <update_message></update_message> tags, create a headline in 10 words or less in <headline></headline> tags.
Also within the <update_message> tags, provide 1-2 sentences to reflect on
what happened last and what you will be doing in <detail></detail> tags written in first person.
You must always have <update_message> in your outputs. For example, your update message
would look like:
<update_message>
<headline>Headline</headline>
<detail>Detail</detail>
</update_message>

Revise your <current_plan> as needed throughout your execution.
</complex_requests>

Your final response must always be in <final_response></final_response> tags. 
Always include update messages before tool use and responses. 
Always include <final_response></final_response> tags when ending your turn.

Make sure to not end your turn using end_turn until your entire plan is completed.
{current_plan}
"""


class BrowserAgent(BaseAgent):
    """Specialized agent for browsing"""

    system_message: SystemMessage = SystemMessage(
        text=WEB_BROWSER_SYSTEM_PROMPT_TEMPLATE
    )
    browser_context: BrowserContext | None = Field(
        default=None, description="The BrowserContext object"
    )
    headless: bool = Field(
        default=False,
        description="If True, the browser will run headless. Default=False",
    )

    async def start_browser(self):
        web_browser_tool_group = await WebBrowserToolGroup.create(
            headless=self.headless
        )
        self.add_tool_group(web_browser_tool_group)
        self.browser_context = web_browser_tool_group.browser_context

    async def _apre_invocation_processing(self):
        # Add browser context last
        if (
            self.browser_context.browser_initialized
            and self.browser_context
            and self.browser_context.current_page
        ):
            await self.browser_context.update()

            # Get the last tool result user message
            tool_result_message = self.get_messages()[-1]

            for content_block in await self.browser_context.format():
                tool_result_message.append_content(content_block)

    async def _apost_invocation_processing(self):
        """
        Executes post invocation processing steps
        """

        # Handle content block retention
        logger.info("Deleting content blocks with retention")
        self.set_messages(
            delete_tool_result_blocks_after_next_turn(self.get_messages())
        )

        last_message = self.get_messages()[-1]
        if self.update_callback and last_message.update_message:
            self.update_callback(last_message.update_message)
