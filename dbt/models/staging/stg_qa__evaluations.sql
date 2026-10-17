-- Grain: one row per QA evaluation of one interaction leg.
select
    evaluation_id,
    leg_id,
    agent_id,
    evaluated_at                    as evaluated_at_utc,
    knowledge_score,
    compliance_score,
    soft_skills_score,
    (knowledge_score + compliance_score + soft_skills_score) / 3.0 as overall_score
from {{ source('qa', 'evaluations') }}
