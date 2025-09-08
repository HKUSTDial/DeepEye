import asyncio
import traceback
from app.agent.deepeye import DeepEyeAgent
from app.logger import logger


async def main():
    agent = DeepEyeAgent()
    try:
        while True:
            logger.info("💬 Enter your request: ")
            user_request = input()
            if not user_request.strip():
                logger.error("❌ Request cannot be empty")
                return
            logger.info(f"🎯 User request: {user_request}")
            logger.info(f"🚀 Agent {agent.name} is running...")
            await agent.run(user_request)
            logger.info(f"✅ Agent {agent.name} has finished the interaction")
    except KeyboardInterrupt:
        logger.info("⏹️ User interrupted the interaction")
        return
    except Exception as e:
        traceback.print_exc()
        logger.error(f"💥 Error: {e}")
        return

if __name__ == "__main__":
    asyncio.run(main())