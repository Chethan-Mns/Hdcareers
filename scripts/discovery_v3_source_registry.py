"""Official-employer registry. Probe-only sources cannot generate publishable jobs.

All hosts below are first-party employer career sites, not third-party job boards.
Provider fingerprints only choose an adapter after live tests validate its coverage.
"""
from dataclasses import dataclass
from urllib.parse import urlsplit

@dataclass(frozen=True)
class Employer:
    name: str
    url: str
    host: str
    family: str
    stage: str
    area: str = "India"

    def __post_init__(self):
        parsed = urlsplit(self.url)
        if parsed.scheme != "https" or parsed.hostname != self.host or not parsed.path:
            raise ValueError(f"Unsafe employer endpoint: {self.name}")
        if self.stage not in {"shadow", "probe_only"}:
            raise ValueError(f"Unsupported stage: {self.name}")

    @property
    def supports_unattended_publishing(self):
        # Provider adapter gates are separate from per-job source and content gates.
        return False


EMPLOYERS = (
    Employer("Deloitte South Asia",
             "https://southasiacareers.deloitte.com/go/Deloitte-India/718244/",
             "southasiacareers.deloitte.com","successfactors","shadow"),
    Employer("EY",
             "https://careers.ey.com/ey/search/",
             "careers.ey.com","successfactors","shadow"),
    Employer("HCLTech",
             "https://careers.hcltech.com/go/India/9553955/",
             "careers.hcltech.com","dynamic-successfactors","shadow"),
    Employer("Accenture",
             "https://www.accenture.com/in-en/careers/jobsearch",
             "www.accenture.com","custom-search","probe_only"),
    Employer("Capgemini",
             "https://jobs.capgemini.com/in-en",
             "jobs.capgemini.com","needs-fingerprint","probe_only"),
    Employer("Wipro",
             "https://careers.wipro.com/",
             "careers.wipro.com","needs-fingerprint","probe_only"),
    Employer("TCS",
             "https://www.tcs.com/careers/india",
             "www.tcs.com","custom-search","probe_only"),
    Employer("Infosys",
             "https://career.infosys.com/jobs",
             "career.infosys.com","custom-search","probe_only"),
    Employer("Tech Mahindra",
             "https://careers.techmahindra.com/Currentopportunity.aspx",
             "careers.techmahindra.com","custom-search","probe_only"),
    Employer("PwC India",
             "https://www.pwc.in/careers.html",
             "www.pwc.in","custom-redirect","probe_only"),
    Employer("KPMG India",
             "https://kpmg.com/in/en/careers.html",
             "kpmg.com","multiple-portals","probe_only"),
)
BY_NAME = {source.name: source for source in EMPLOYERS}


def adapter_status():
    return [{"employer": source.name, "official": source.url,
             "type": source.family, "stage": source.stage,
             "canAutoPublish": source.supports_unattended_publishing}
            for source in EMPLOYERS]


def fingerprint(html, content_type="text/html"):
    """Weak platform clue. Never use its output as job/expiry evidence."""
    if "html" not in content_type.lower():
        return "unknown"
    s = html.lower()
    if "career site company id" in s or "rmkcdn.successfactors.com" in s or \
            "career site by successfactors" in s:
        return "successfactors-like"
    if "myworkdayjobs.com" in s or "workday" in s and "requisition" in s:
        return "workday-like"
    if "job-boards.greenhouse.io" in s or "boards.greenhouse.io" in s:
        return "greenhouse-like"
    if "jobs.lever.co" in s:
        return "lever-like"
    return "custom-or-unrecognized"
