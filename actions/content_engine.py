"""
Content Creation Pipeline — Part 3.5.3: Automated content with approval gates.
Ideation → Drafting → Review → Publish → Monetize → Track.
"""
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from core.domain_agent import DomainAgent, DomainConfig
from core.safety_guardian import is_killed, is_breaker_tripped, increment_scope
from core.audit_log import write_audit_entry

class ContentEngineAgent(DomainAgent):
    """Content creation pipeline with approval gates per channel."""
    
    def __init__(self):
        config = DomainConfig(
            domain="content",
            autonomy_level=1,
            target_ceiling=4,
            caps={
                "max_posts_per_day": 20,
                "max_channels": 10
            },
            always_requires_approval=[
                "publish_post", "schedule_post", "monetize_channel",
                "run_ads", "affiliate_link"
            ],
            allowlist=[]
        )
        super().__init__(config)
        self._channels = {
            "blog": {"platform": "ghost", "autonomy_level": 1, "track_record": 0},
            "twitter": {"platform": "twitter", "autonomy_level": 1, "track_record": 0},
            "linkedin": {"platform": "linkedin", "autonomy_level": 1, "track_record": 0},
            "medium": {"platform": "medium", "autonomy_level": 1, "track_record": 0},
            "devto": {"platform": "dev.to", "autonomy_level": 1, "track_record": 0},
            "youtube": {"platform": "youtube", "autonomy_level": 1, "track_record": 0}
        }
        self._ai_disclosure = True
        self._content_queue: List[Dict] = []
        self._published: List[Dict] = []
        self._drafts: Dict = {}
        
    async def handle(self, action: str, params: Dict) -> Any:
        if is_killed("content"):
            return {"success": False, "error": "Content domain killed by safety guardian"}
            
        if action == "create_content":
            return await self._create_content(params)
        elif action == "draft_content":
            return await self._draft_content(params)
        elif action == "review_content":
            return await self._review_content(params)
        elif action == "publish_content":
            return await self._publish_content(params)
        elif action == "schedule_content":
            return await self._schedule_content(params)
        elif action == "get_queue":
            return await self._get_queue()
        elif action == "get_analytics":
            return await self._get_analytics(params)
        elif action == "monetize":
            return await self._monetize(params)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
            
    async def _create_content(self, params: Dict) -> Dict:
        """Ideation + drafting from opportunity or prompt."""
        topic = params.get("topic", params.get("prompt", ""))
        content_type = params.get("type", "blog")
        channel = params.get("channel", "blog")
        
        # Generate draft
        draft = await self._generate_draft(topic, content_type, channel)
        
        draft_id = f"draft_{int(time.time())}"
        draft["id"] = draft_id
        draft["created"] = datetime.now(timezone.utc).isoformat()
        draft["status"] = "draft"
        
        self._drafts[draft_id] = draft
        
        return {"success": True, "draft": draft}
        
    async def _generate_draft(self, topic: str, content_type: str, channel: str) -> Dict:
        """Generate content draft - would use LLM in production."""
        templates = {
            "blog": {
                "title": f"Complete Guide to {topic}",
                "outline": [
                    f"Introduction to {topic}",
                    f"Why {topic} Matters in 2024",
                    f"Getting Started with {topic}",
                    f"Advanced {topic} Techniques",
                    f"Common Mistakes to Avoid",
                    f"Conclusion and Next Steps"
                ],
                "word_count": 2000
            },
            "twitter": {
                "title": f"Thread: {topic}",
                "outline": [
                    f"1/ {topic} is changing how we work. Here's why:",
                    f"2/ The problem: traditional approaches fail because...",
                    f"3/ The solution: {topic} solves this by...",
                    f"4/ Real example: how I used {topic} to...",
                    f"5/ Key takeaway: {topic} isn't just a tool, it's a mindset.",
                    f"6/ Want to learn more? Link in bio."
                ],
                "word_count": 280
            },
            "linkedin": {
                "title": f"How {topic} Transformed My Workflow",
                "outline": [
                    "The challenge I faced",
                    f"How {topic} provided the solution",
                    "Measurable results",
                    "Key lessons learned",
                    "Call to action"
                ],
                "word_count": 1300
            }
        }
        
        template = templates.get(channel, templates["blog"])
        
        return {
            "type": content_type,
            "channel": channel,
            "topic": topic,
            "title": template["title"],
            "outline": template["outline"],
            "target_word_count": template["word_count"],
            "ai_disclosure": self._ai_disclosure
        }
        
    async def _draft_content(self, params: Dict) -> Dict:
        """Create full draft from outline."""
        draft_id = params.get("draft_id")
        if draft_id not in self._drafts:
            return {"success": False, "error": "Draft not found"}
            
        draft = self._drafts[draft_id]
        draft["status"] = "drafted"
        draft["drafted_at"] = datetime.now(timezone.utc).isoformat()
        
        # Add AI disclosure if required
        if self._ai_disclosure:
            draft["disclosure"] = "This content was created with AI assistance."
            
        return {"success": True, "draft": draft}
        
    async def _review_content(self, params: Dict) -> Dict:
        draft_id = params.get("draft_id")
        action = params.get("action")  # "approve" | "reject" | "revise"
        
        if draft_id not in self._drafts:
            return {"success": False, "error": "Draft not found"}
            
        draft = self._drafts[draft_id]
        
        if action == "approve":
            draft["status"] = "approved"
            draft["approved_at"] = datetime.now(timezone.utc).isoformat()
            return {"success": True, "draft": draft}
        elif action == "reject":
            draft["status"] = "rejected"
            draft["rejection_reason"] = params.get("reason", "")
            return {"success": True, "draft": draft}
        elif action == "revise":
            draft["status"] = "revision_requested"
            draft["revision_notes"] = params.get("notes", "")
            return {"success": True, "draft": draft}
        else:
            return {"success": False, "error": "Invalid action"}
            
    async def _publish_content(self, params: Dict) -> Dict:
        draft_id = params.get("draft_id")
        channel = params.get("channel", "blog")
        
        if draft_id not in self._drafts:
            return {"success": False, "error": "Draft not found"}
            
        draft = self._drafts[draft_id]
        if draft["status"] != "approved":
            return {"success": False, "error": "Draft not approved", "requires_approval": True}
            
        # Check channel autonomy level
        channel_config = self._channels.get(channel, {})
        channel_level = channel_config.get("autonomy_level", 1)
        track_record = channel_config.get("track_record", 0)
        
        # Check if channel has earned autonomous publishing
        if channel_level < 4 and track_record < 10:
            return {"success": False, "error": f"Channel {channel} requires approval (level {channel_level}, {track_record} posts)", "requires_approval": True}
            
        # Check rate limit
        if is_breaker_tripped("scope_published_per_day"):
            return {"success": False, "error": "Daily publish limit reached"}
            
        increment_scope("scope_published_per_day")
        
        # Publish to platform
        result = await self._publish_to_platform(draft, channel)
        
        if result.get("success"):
            draft["status"] = "published"
            draft["published_at"] = datetime.now(timezone.utc).isoformat()
            draft["channel"] = channel
            draft["platform_id"] = result.get("platform_id")
            self._published.append(draft)
            del self._drafts[draft_id]
            
            # Update channel track record
            channel_config["track_record"] += 1
            
            # Log with AI disclosure
            log_audit("content", f"publish:{draft_id}", "passed", 
                     "auto_approved" if track_record >= 10 else "approved_by_boss",
                     "success", {"platform_id": result.get("platform_id")}, 
                     f"Published to {channel}")
            
        return result
        
    async def _publish_to_platform(self, draft: Dict, channel: str) -> Dict:
        return {
            "success": False,
            "error": f"Publishing for {channel} is not connected. The draft was not published.",
        }
        
    async def _schedule_content(self, params: Dict) -> Dict:
        return {
            "success": False,
            "error": "No publishing scheduler is connected. The content was not scheduled.",
        }
        
    async def _get_queue(self) -> Dict:
        return {
            "drafts": len(self._drafts),
            "scheduled": 0,
            "published_today": 0
        }
        
    async def _get_analytics(self, params: Dict) -> Dict:
        return {"success": False, "error": "No channel analytics integration is connected."}
        
    async def _monetize(self, params: Dict) -> Dict:
        return {"success": False, "error": "No monetization provider is connected. No account was changed."}
        
    def get_status(self) -> Dict:
        return {
            "domain": "content",
            "autonomy_level": 1,
            "target_ceiling": 4,
            "drafts": len(self._drafts),
            "published": len(self._published),
            "channels": list(self._channels.keys())
        }
        
    def get_proposals(self) -> List[Dict]:
        return []


_content_engine_agent: ContentEngineAgent | None = None


def handle(parameters: Dict | None = None, response=None, player=None, session_memory=None) -> Dict[str, Any]:
    """Adapt JARVIS's content-tool schema to the draft-only content agent."""
    global _content_engine_agent
    params = dict(parameters or {})
    action = str(params.pop("action", "")).strip().lower()
    if not action:
        return {"success": False, "error": "Choose a content-engine action."}
    if _content_engine_agent is None:
        _content_engine_agent = ContentEngineAgent()
    try:
        if action == "status":
            return {"success": True, "status": _content_engine_agent.get_status()}
        content_types = {"blog", "tutorial", "comparison", "description", "seo"}
        if action not in content_types:
            return {"success": False, "error": f"Unsupported content action: {action}"}
        topic = str(params.get("target", "")).strip()
        if not topic:
            return {"success": False, "error": f"Provide a topic or product for the {action} draft."}
        return asyncio.run(_content_engine_agent.handle("create_content", {
            "topic": topic,
            "type": action,
            "channel": "blog",
            "style": params.get("value", ""),
        }))
    except Exception as exc:
        return {"success": False, "error": f"Content engine failed: {exc}"}
