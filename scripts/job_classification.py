"""Job category and experience rules for HD Careers page generation and publishing.

Internships/apprenticeships are independent of full-time fresher/experienced.
Technical work is IT; BPO, sales, and support work is Non-IT.
"""
from __future__ import annotations
import re

TRAINING = re.compile(r"\b(?:intern|internship|apprentice|apprenticeship)\b", re.I)
NON_IT = re.compile(
    r"\b(?:bpo|call[ -]?cent(?:er|re)|contact[ -]?cent(?:er|re)|customer[ -]?(?:support|service|care|success)"
    r"|client[ -]?support|support|service[ -]?desk|help[ -]?desk|sales|business[ -]?development"
    r"|marketing|recruit(?:ment|er|ing)?|talent[ -]?(?:operations|acquisition)|human[ -]?resources"
    r"|hr[ -]?(?:associate|executive|recruiter)|billing|collections?|telecaller|voice[ -]?process"
    r"|non[ -]?voice|back[ -]?office|tax|audit|accounting|finance|operations[ -]?associate"
    r"|relationship[ -]?manager)\b", re.I,
)
TECHNICAL = re.compile(
    r"\b(?:software|developer|development[ -]?engineer|programmer|coding|java(?:script)?|python|c\+\+"
    r"|c#|typescript|react|angular|node\.?js|sql|nosql|database|backend|front[ -]?end"
    r"|full[ -]?stack|devops|cloud|aws|azure|databricks|snowflake|pyspark|hadoop|kafka"
    r"|api|machine[ -]?learning|data[ -]?(?:engineer|scientist|science|analyst)|cyber"
    r"|network(?:ing)?|linux|computer[ -]?science|information[ -]?technology|qa[ -]?engineer"
    r"|automation[ -]?engineer|test[ -]?engineer|embedded|electronic(?:s)?|vlsi|cad"
    r"|design[ -]?engineer|technical)\b", re.I,
)
ENTRY = re.compile(
    r"\b(?:freshers?|fresh[ -]?grad(?:uate)?s?|new[ -]?grad(?:uate)?s?|no[ -]?(?:prior[ -]?)?experience"
    r"|zero[ -]?experience|entry[ -]?level|campus[ -]?(?:hire|hiring|graduate)"
    r"|graduate[ -]?trainee|university[ -]?graduate)\b", re.I,
)
DURATION = re.compile(r"\b(\d+)\s*(?:[-–—]|to)\s*(\d+)\s*(?:years?|yrs?)\b|\b(\d+)\s*\+?\s*(?:years?|yrs?)\b", re.I)


def is_training(job):
    cat = str(job.get("cat") or "").lower()
    return cat in ("internship", "apprenticeship") or bool(TRAINING.search(str(job.get("role") or job.get("roleTag") or "")))


def min_years(text):
    raw = str(text or "")
    for word, value in (("one", "1"), ("two", "2"), ("three", "3"), ("four", "4")):
        raw = re.sub(r"\b" + word + r" years?\b", value + " years", raw, flags=re.I)
    values = [int(m.group(1) or m.group(3)) for m in DURATION.finditer(raw)]
    return min(values) if values else None


def experience_type(job):
    years = str(job.get("expYears") or job.get("experience") or "")
    role = str(job.get("role") or "")
    minimum = min_years(years)
    if minimum is None:
        minimum = min_years(job.get("elig"))
    if minimum is not None:
        return "fresher" if minimum == 0 else "experienced"
    if re.search(r"\b(?:less than|under|up to|upto)\s+[1-9]\d*\s*(?:years?|yrs?)\b", years, re.I):
        return "fresher"
    if ENTRY.search(years + " " + role):
        return "fresher"
    explicit = str(job.get("expType") or "").lower()
    return explicit if explicit in ("fresher", "experienced") else "not-specified"


def field_type(job):
    role = str(job.get("role") or job.get("roleTag") or "")
    if NON_IT.search(role):
        return "nonit"
    skills = " ".join(map(str, job.get("skills") or []))
    if TECHNICAL.search(role + " " + skills):
        return "it"
    cat = str(job.get("cat") or "").lower()
    if cat in ("nonit", "non-it", "non it"):
        return "nonit"
    if cat == "it":
        return "it"
    return "it" if job.get("field") == "it" else "nonit"


def classified(job):
    training = is_training(job)
    field = field_type(job)
    exp_type = experience_type(job)
    cat = str(job.get("cat") or "").lower()
    if training:
        cat = "apprenticeship" if (cat == "apprenticeship" or re.search(r"\bapprentice(ship)?\b", str(job.get("role") or ""), re.I)) else "internship"
    elif cat in ("it", "nonit", "non it", "non-it", ""):
        cat = field
    return {"cat": cat, "field": field, "expType": exp_type, "training": training}
