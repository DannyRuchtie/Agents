import asyncio
from agents.vision_agent import VisionAgent

async def analyze():
    agent = VisionAgent()
    prompt = """Please analyze this image in detail, focusing on:
1. Location and setting
2. Landscape features
3. Architecture or structures
4. Colors and lighting
5. Overall atmosphere
6. Any unique or notable features"""
    
    result = await agent.analyze_image('/Users/danny/Desktop/licensed-image.jpeg', prompt)
    print(result)

if __name__ == "__main__":
    asyncio.run(analyze()) 