import asyncio
from typing import Any, Callable, Dict, List, Union

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.prebuilt.tool_node import ToolNode


class ParallelToolNode(ToolNode):
    """自定义 ToolNode，确保并行执行多个工具调用"""
    
    def __init__(self, tools: Union[List[BaseTool], List[Callable]]) -> None:
        super().__init__(tools)
    
    async def ainvoke(self, input: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
        """异步调用工具，并行执行多个工具"""
        if isinstance(input, list):
            output = await asyncio.gather(*[
                self._arun_one(i, config) for i in input
            ])
            return output
        else:
            return await self._arun_one(input, config)
    
    async def _arun_one(self, input: Dict[str, Any], config: RunnableConfig = None) -> Dict[str, Any]:
        """执行单个工具调用请求"""
        message = input.get("messages", [])[-1] if input.get("messages") else None
        
        if not message or not hasattr(message, "tool_calls") or not message.tool_calls:
            return {"messages": []}
        
        tool_calls = message.tool_calls
        tool_map = {tool.name: tool for tool in self.tools_by_name.values()}
        
        # 并行执行所有工具调用
        tasks = []
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call.get("id", "")
            
            if tool_name in tool_map:
                tool = tool_map[tool_name]
                tasks.append(self._execute_tool(tool, tool_args, tool_call_id, config))
        
        # 使用 asyncio.gather 并行执行
        tool_messages = await asyncio.gather(*tasks)
        
        return {"messages": tool_messages}
    
    async def _execute_tool(
        self, 
        tool: BaseTool, 
        tool_args: Dict[str, Any], 
        tool_call_id: str,
        config: RunnableConfig = None
    ) -> ToolMessage:
        """执行单个工具并返回 ToolMessage"""
        try:
            # 检查工具是否是异步的
            if hasattr(tool, 'ainvoke'):
                result = await tool.ainvoke(tool_args, config=config)
            else:
                result = await asyncio.to_thread(tool.invoke, tool_args, config)
            
            return ToolMessage(
                content=str(result),
                tool_call_id=tool_call_id,
                name=tool.name
            )
        except Exception as e:
            return ToolMessage(
                content=f"Error executing tool {tool.name}: {str(e)}",
                tool_call_id=tool_call_id,
                name=tool.name
            )
