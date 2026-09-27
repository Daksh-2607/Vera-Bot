"""
Message Composer — deterministic message generation.

Architecture:
1. Context validation
2. Signal extraction
3. Template selection (based on trigger kind)
4. Template rendering (deterministic substitution)
5. Optional LLM polishing (if API key present)
6. Output validation

This keeps the decision deterministic; LLM is only for wording, not logic.
"""

from typing import Optional, Dict, Any, Tuple
from engine.context_store import get_store
import json
import re


class MessageComposer:
    """Composes messages from 4-context framework."""
    
    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        self.store = get_store()
    
    def compose_message(self, trigger_kind, category, merchant, customer, trigger_data=None):
        """
        Compose personalized messages based on category, trigger, and merchant data.
        Uses category-specific voice, offers, and insights.
        """
        
        # DENTISTS
        if category == "dentists":
            if trigger_kind == "recall_due":
                customer_name = customer.get('name', 'there') if customer else 'there'
                merchant_name = merchant.get('name', 'our clinic') if merchant else 'our clinic'
                return {
                    "body": f"Hi {customer_name}, your 3-month recall is due at {merchant_name}. "
                            f"Book now for scaling + fluoride varnish checkup. Limited slots available.",
                    "cta": "Book Appointment",
                    "template_name": "dentist_recall_due",
                    "rationale": "Category-specific recall with clinical detail + urgency"
                }
            
            elif trigger_kind == "perf_spike":
                merchant_name = merchant.get('name', 'clinic') if merchant else 'clinic'
                return {
                    "body": f"{merchant_name} just hit a new rating peak! "
                            f"New digital impression setup + CAD/CAM crowns (done in 90 min). "
                            f"Free consultation available.",
                    "cta": "Learn More",
                    "template_name": "dentist_perf_spike",
                    "rationale": "Performance spike with tech innovation angle"
                }
            
            elif trigger_kind == "dormant_with_vera":
                merchant_name = merchant.get('name', 'clinic') if merchant else 'clinic'
                return {
                    "body": f"It's been a while! {merchant_name} now offers advanced treatments. "
                            f"Scaling @ ₹299, IPS e.max crowns @ ₹3,200. Your smile, our focus.",
                    "cta": "Book Now",
                    "template_name": "dentist_dormant",
                    "rationale": "Re-engagement with specific pricing + service upgrades"
                }
        
        # RESTAURANTS
        elif category == "restaurants":
            if trigger_kind == "perf_spike":
                merchant_name = merchant.get('name', 'restaurant') if merchant else 'restaurant'
                dish = trigger_data.get('dish', 'new dish') if trigger_data else 'new dish'
                return {
                    "body": f"🔥 {merchant_name} is trending! {dish} just launched. "
                            f"Only 3 tables left this evening. Grab a spot now.",
                    "cta": "Reserve Table",
                    "template_name": "restaurant_perf_spike",
                    "rationale": "Performance spike with scarcity + new offering"
                }
            
            elif trigger_kind == "review_theme_emerged":
                merchant_name = merchant.get('name', 'restaurant') if merchant else 'restaurant'
                theme = trigger_data.get('theme', 'quality') if trigger_data else 'quality'
                return {
                    "body": f"Customers are raving about {theme} at {merchant_name}! "
                            f"Join 200+ happy diners — book your table today.",
                    "cta": "Reserve Now",
                    "template_name": "restaurant_review_theme",
                    "rationale": "Review theme with social proof"
                }
            
            elif trigger_kind == "festival_upcoming":
                merchant_name = merchant.get('name', 'restaurant') if merchant else 'restaurant'
                festival = trigger_data.get('festival', 'celebration') if trigger_data else 'celebration'
                return {
                    "body": f"{festival} coming up! {merchant_name} is offering festive menus. "
                            f"Early bookings get 20% off. Reserve now.",
                    "cta": "Book Festive",
                    "template_name": "restaurant_festival",
                    "rationale": "Seasonal opportunity with discount incentive"
                }
        
        # SALONS
        elif category == "salons":
            if trigger_kind == "recall_due":
                customer_name = customer.get('name', 'there') if customer else 'there'
                merchant_name = merchant.get('name', 'salon') if merchant else 'salon'
                return {
                    "body": f"Hi {customer_name}, your next appointment at {merchant_name} is due! "
                            f"New treatments: Keratin + Threading combo @ ₹799. Saturday slots available.",
                    "cta": "Book Stylist",
                    "template_name": "salon_recall",
                    "rationale": "Recall with new service bundle + specific availability"
                }
            
            elif trigger_kind == "perf_spike":
                merchant_name = merchant.get('name', 'salon') if merchant else 'salon'
                return {
                    "body": f"✨ {merchant_name} is trending! Fresh looks trending now. "
                            f"Book your transformation this week.",
                    "cta": "Book Now",
                    "template_name": "salon_perf_spike",
                    "rationale": "Performance spike with aesthetic appeal"
                }
            
            elif trigger_kind == "milestone_reached":
                merchant_name = merchant.get('name', 'salon') if merchant else 'salon'
                milestone = trigger_data.get('milestone', '100 reviews') if trigger_data else '100 reviews'
                return {
                    "body": f"🎉 {merchant_name} hit {milestone}! Thank you to all our clients. "
                            f"This week: 25% off all services. Celebrate with us!",
                    "cta": "Claim Offer",
                    "template_name": "salon_milestone",
                    "rationale": "Milestone celebration with thank-you offer"
                }
        
        # GYMS
        elif category == "gyms":
            if trigger_kind == "milestone_reached":
                customer_name = customer.get('name', 'you') if customer else 'you'
                merchant_name = merchant.get('name', 'gym') if merchant else 'gym'
                milestone = trigger_data.get('milestone', '10') if trigger_data else '10'
                return {
                    "body": f"🎉 {customer_name}! You've hit {milestone} sessions at {merchant_name}. "
                            f"You've earned a free protein shake. Congrats on your consistency!",
                    "cta": "Claim Reward",
                    "template_name": "gym_milestone",
                    "rationale": "Personal milestone with reward + encouragement"
                }
            
            elif trigger_kind == "perf_dip":
                merchant_name = merchant.get('name', 'gym') if merchant else 'gym'
                return {
                    "body": f"We miss you at {merchant_name}! Come back this week for 5 sessions "
                            f"and get 2 free PT consultations. Your progress matters.",
                    "cta": "Check Schedule",
                    "template_name": "gym_perf_dip",
                    "rationale": "Re-engagement with value-add + motivation"
                }
            
            elif trigger_kind == "perf_spike":
                merchant_name = merchant.get('name', 'gym') if merchant else 'gym'
                return {
                    "body": f"🔥 {merchant_name} is booked out! New early morning classes just added. "
                            f"Join our peak-time squad — membership bonus this month.",
                    "cta": "Join Now",
                    "template_name": "gym_perf_spike",
                    "rationale": "Performance spike with scarcity + new offering"
                }
        
        # PHARMACIES
        elif category == "pharmacies":
            if trigger_kind == "recall_due":
                customer_name = customer.get('name', 'there') if customer else 'there'
                merchant_name = merchant.get('name', 'pharmacy') if merchant else 'pharmacy'
                return {
                    "body": f"Hi {customer_name}, your prescription refill is ready at {merchant_name}. "
                            f"Pick up today — 15% off + free home delivery on next order.",
                    "cta": "Refill Now",
                    "template_name": "pharmacy_recall",
                    "rationale": "Recall with incentive + convenience"
                }
            
            elif trigger_kind == "perf_spike":
                merchant_name = merchant.get('name', 'pharmacy') if merchant else 'pharmacy'
                brand = trigger_data.get('brand', 'premium brands') if trigger_data else 'premium brands'
                return {
                    "body": f"{merchant_name} now stocks {brand}. "
                            f"Same-day delivery available. Order online now.",
                    "cta": "Browse",
                    "template_name": "pharmacy_perf_spike",
                    "rationale": "New inventory with service highlight"
                }
            
            elif trigger_kind == "milestone_reached":
                merchant_name = merchant.get('name', 'pharmacy') if merchant else 'pharmacy'
                return {
                    "body": f"{merchant_name} is now rated 4.8★! Trusted by thousands. "
                            f"Free consultation with pharmacist for health queries.",
                    "cta": "Learn More",
                    "template_name": "pharmacy_milestone",
                    "rationale": "Rating milestone with service benefit"
                }
        
        # Fallback for unknown trigger/category combo
        return self._compose_generic(category, merchant, trigger_data, customer)
    
    def _compose_research_digest(self, category, merchant, trigger, customer):
        """Research/knowledge trigger."""
        payload = trigger.payload
        top_item_id = payload.get("top_item_id")
        
        digest_items = category.payload.get("digest", [])
        item = None
        for d in digest_items:
            if d.get("id") == top_item_id:
                item = d
                break
        
        if not item:
            return None
        
        merchant_name = merchant.payload.get("identity", {}).get("name", "there")
        merchant_name_part = merchant_name.split()[0] if merchant_name else "there"
        
        # Build message
        title = item.get("title", "")
        source = item.get("source", "")
        summary = item.get("summary", "")
        patient_segment = item.get("patient_segment", "")
        
        lines = [
            f"{merchant_name_part}, {source} just landed. ",
        ]
        
        if patient_segment:
            lines.append(f"One item relevant to your {patient_segment} — ")
        else:
            lines.append("One item caught our eye — ")
        
        lines.append(f"{summary} ")
        lines.append(f"Worth a look (2-min read). Want me to pull it + draft a note you can share with clients?")
        
        body = "".join(lines)
        
        return {
            "body": body,
            "cta": "open_ended",
            "template_name": "research_digest_v1",
            "template_params": [merchant_name_part, top_item_id, source],
            "rationale": f"External research digest with category anchor; merchant is {merchant.payload.get('category_slug')} with {patient_segment or 'general'} focus"
        }
    
    def _compose_perf_spike(self, category, merchant, trigger, customer):
        """Performance spike trigger."""
        perf = merchant.payload.get("performance", {})
        
        # Check what spiked
        delta_7d = perf.get("delta_7d", {})
        views_pct = delta_7d.get("views_pct", 0)
        calls_pct = delta_7d.get("calls_pct", 0)
        
        merchant_name = merchant.payload.get("identity", {}).get("name", "")
        merchant_name_part = merchant_name.split()[0] if merchant_name else "there"
        
        best_metric = "views"
        best_delta = views_pct
        if abs(calls_pct) > abs(views_pct):
            best_metric = "calls"
            best_delta = calls_pct
        
        delta_str = f"+{int(best_delta*100)}%" if best_delta > 0 else f"{int(best_delta*100)}%"
        
        body = f"{merchant_name_part}, your {best_metric} are up {delta_str} this week. Want me to identify what changed so you can repeat it?"
        
        return {
            "body": body,
            "cta": "yes_no",
            "template_name": "perf_spike_v1",
            "template_params": [merchant_name_part, best_metric, delta_str],
            "rationale": f"Performance spike in {best_metric}; opportunity to identify and repeat success factors"
        }
    
    def _compose_perf_dip(self, category, merchant, trigger, customer):
        """Performance dip trigger."""
        perf = merchant.payload.get("performance", {})
        peer_stats = category.payload.get("peer_stats", {})
        
        ctr = perf.get("ctr", 0)
        avg_ctr = peer_stats.get("avg_ctr", 0)
        
        merchant_name = merchant.payload.get("identity", {}).get("name", "")
        merchant_name_part = merchant_name.split()[0] if merchant_name else "there"
        
        if ctr < avg_ctr:
            body = f"{merchant_name_part}, your CTR is {ctr:.1%}, below the {avg_ctr:.1%} peer average. Want me to suggest one profile change tied to this?"
            return {
                "body": body,
                "cta": "yes_no",
                "template_name": "perf_dip_v1",
                "template_params": [merchant_name_part, f"{ctr:.1%}", f"{avg_ctr:.1%}"],
                "rationale": f"Performance dip; CTR below peer median; opportunity to optimize profile"
            }
        
        return None
    
    def _compose_recall_due(self, category, merchant, trigger, customer):
        """Customer recall reminder trigger (customer scope)."""
        if not customer:
            return None
        
        customer_name = customer.payload.get("identity", {}).get("name", "")
        merchant_name = merchant.payload.get("identity", {}).get("name", "")
        
        offers = merchant.payload.get("offers", [])
        active_offer = None
        for o in offers:
            if o.get("status") == "active":
                active_offer = o
                break
        
        offer_text = ""
        if active_offer:
            offer_text = f". {active_offer.get('title', '')} available"
        
        body = f"Hi {customer_name}, it's been a while since your last visit{offer_text}. Ready to book?"
        
        return {
            "body": body,
            "cta": "open_ended",
            "template_name": "recall_due_v1",
            "template_params": [customer_name, active_offer.get("title", "") if active_offer else ""],
            "rationale": f"Customer recall due; personalized with active offer"
        }
    
    def _compose_milestone(self, category, merchant, trigger, customer):
        """Milestone reached (e.g., 100 reviews)."""
        merchant_name = merchant.payload.get("identity", {}).get("name", "")
        merchant_name_part = merchant_name.split()[0] if merchant_name else "there"
        
        milestone = trigger.payload.get("milestone_type", "reviews")
        milestone_value = trigger.payload.get("milestone_value", 100)
        
        body = f"{merchant_name_part}, congrats—you've hit {milestone_value} {milestone}! Want me to draft a thank-you note for your customers?"
        
        return {
            "body": body,
            "cta": "open_ended",
            "template_name": "milestone_v1",
            "template_params": [merchant_name_part, str(milestone_value)],
            "rationale": "Milestone celebration; engagement opportunity"
        }
    
    def _compose_dormant(self, category, merchant, trigger, customer):
        """Merchant dormant / no contact for 14+ days."""
        merchant_name = merchant.payload.get("identity", {}).get("name", "")
        merchant_name_part = merchant_name.split()[0] if merchant_name else "there"
        
        body = f"{merchant_name_part}, it's been quiet. Anything I can help you with—profile updates, customer recalls, campaign ideas?"
        
        return {
            "body": body,
            "cta": "open_ended",
            "template_name": "dormant_v1",
            "template_params": [merchant_name_part],
            "rationale": "Re-engagement; offering multiple value propositions"
        }
    
    def _compose_festival(self, category, merchant, trigger, customer):
        """Festival/seasonal opportunity."""
        festival = trigger.payload.get("festival_name", "festival")
        days_until = trigger.payload.get("days_until", 0)
        
        merchant_name = merchant.payload.get("identity", {}).get("name", "")
        merchant_name_part = merchant_name.split()[0] if merchant_name else "there"
        
        body = f"{merchant_name_part}, {festival} is in {days_until} days. Want me to draft a campaign + offer to boost visibility?"
        
        return {
            "body": body,
            "cta": "yes_no",
            "template_name": "festival_v1",
            "template_params": [merchant_name_part, festival],
            "rationale": f"Seasonal opportunity; time-sensitive (expires in {days_until} days)"
        }
    
    def _compose_review_theme(self, category, merchant, trigger, customer):
        """Review theme emerged (e.g., 3 mentions of 'wait time')."""
        theme = trigger.payload.get("theme", "")
        
        merchant_name = merchant.payload.get("identity", {}).get("name", "")
        merchant_name_part = merchant_name.split()[0] if merchant_name else "there"
        
        body = f"{merchant_name_part}, 3+ reviews this week mention '{theme}'. Want me to draft a response?"
        
        return {
            "body": body,
            "cta": "yes_no",
            "template_name": "review_theme_v1",
            "template_params": [merchant_name_part, theme],
            "rationale": f"Reputation issue; proactive management opportunity"
        }
    
    def _compose_generic(self, category, merchant, trigger, customer):
        """Fallback for unknown trigger types."""
        merchant_name = merchant.get("name", "our service") if isinstance(merchant, dict) else merchant.payload.get("identity", {}).get("name", "")
        merchant_name_part = merchant_name.split()[0] if merchant_name else "there"
        
        body = f"{merchant_name_part}, I have a suggestion for you. Want to hear it?"
        
        return {
            "body": body,
            "cta": "yes_no",
            "template_name": "generic_v1",
            "template_params": [merchant_name_part],
            "rationale": "Generic engagement; safe fallback"
        }