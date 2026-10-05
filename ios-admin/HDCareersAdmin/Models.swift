import Foundation

struct Job: Codable, Hashable, Identifiable {
    var jobId: Int?
    var page: String?
    var domain: String?
    var company: String?
    var salary: String?
    var logo: [String]?
    var careerIconUrl: String?
    var logoUrl: String?
    var role: String?
    var roleTag: String?
    var loc: String?
    var locationFilter: String?
    var batch: String?
    var elig: String?
    var cat: String?
    var expType: String?
    var expYears: String?
    var date: String?
    var desc: String?
    var resp: [String]?
    var apply: String?
    var status: String?
    var verifiedDate: String?
    var sourceName: String?
    var skills: [String]?
    var who: String?
    var closingAt: String?
    var workMode: String?
    var categories: [String]?
    var companyOverview: String?
    var industry: String?
    var headquarters: String?
    var foundedYear: String?
    var companyWebsite: String?
    var careersUrl: String?
    var externalJobId: String?
    var selectionProcess: [String]?
    var importantDates: [String]?

    var id: String {
        page ?? apply ?? "\(company ?? "job")-\(role ?? "role")-\(jobId ?? 0)"
    }

    var isActive: Bool { (status ?? "active") == "active" }
    var isExpired: Bool { status == "expired" }
    var isFresher: Bool { expType == "fresher" }
    var siteURL: URL? {
        guard let page, !page.isEmpty else { return nil }
        return URL(string: "https://hdcareers.in/" + page.trimmingCharacters(in: CharacterSet(charactersIn: "/")))
    }
    var officialURL: URL? { apply.flatMap(URL.init(string:)) }

    enum CodingKeys: String, CodingKey {
        case jobId = "id"
        case page, domain, company, salary, logo, careerIconUrl, logoUrl, role, roleTag, loc, locationFilter
        case batch, elig, cat, expType, expYears, date, desc, resp, apply, status
        case verifiedDate, sourceName, skills, who, closingAt, workMode, categories
        case companyOverview, industry, headquarters, foundedYear, companyWebsite, careersUrl
        case externalJobId = "jobId"
        case selectionProcess, importantDates
    }
}

struct TrafficResponse: Decodable {
    struct Totals: Decodable {
        let visitors: Int?
        let pageviews: Int?
        let sessions: Int?
    }

    struct Page: Decodable, Identifiable {
        let requestPath: String?
        let pageviews: Int?
        var id: String { requestPath ?? UUID().uuidString }
    }

    struct Referrer: Decodable, Identifiable {
        let referrerHostname: String?
        let sessions: Int?
        var id: String { referrerHostname ?? UUID().uuidString }
    }

    struct Country: Decodable, Identifiable {
        let country: String?
        let visitors: Int?
        var id: String { country ?? UUID().uuidString }
    }

    struct Device: Decodable, Identifiable {
        let deviceType: String?
        let visitors: Int?
        var id: String { deviceType ?? UUID().uuidString }
    }

    struct Conversions: Decodable {
        let jobPageViews: Int?
        let jobOpens: Int?
        let applyClicks: Int?
        let applyUsers: Int?
        let resumeChecks: Int?
        let resumeUsers: Int?
        let resumeSamples: Int?
        let shares: Int?
        let socialClicks: Int?
        let applyRate: Double?
    }

    struct ConversionPage: Decodable, Identifiable {
        let requestPath: String?
        let count: Int?
        var id: String { requestPath ?? UUID().uuidString }
    }

    struct ConversionSource: Decodable, Identifiable {
        let referrerHostname: String?
        let count: Int?
        var id: String { referrerHostname ?? UUID().uuidString }
    }

    let configured: Bool?
    let provider: String?
    let days: Int?
    let realtimeUsers: Int?
    let totals: Totals?
    let pages: [Page]?
    let referrers: [Referrer]?
    let countries: [Country]?
    let devices: [Device]?
    let conversions: Conversions?
    let applyJobs: [ConversionPage]?
    let resumeJobs: [ConversionPage]?
    let applySources: [ConversionSource]?
    let refreshedAt: String?
}

struct AutomationHealth: Decodable {
    struct Slot: Decodable, Identifiable {
        let id: String
        let title: String
        let time: String
        let timezone: String?
        let automationId: String?
        let enabled: Bool
        let lastRunAt: String?
        let outcome: String?
        let detail: String?
        let company: String?
        let role: String?
        let page: String?
        let target: String?
        let mix: [String]?
        let delivery: String?
        let nextRunAt: String?
    }

    let updatedAt: String?
    let slots: [Slot]
}

struct AvailabilityResponse: Decodable {
    struct Trigger: Decodable {
        let requestedAt: String?
        let reason: String?
    }

    struct Run: Decodable {
        let id: Int?
        let runNumber: Int?
        let status: String?
        let conclusion: String?
        let event: String?
        let source: String?
        let createdAt: String?
        let updatedAt: String?
        let url: String?
    }

    struct Results: Decodable {
        let checkedAt: String?
        let checked: Int?
        let active: Int?
        let expired: Int?
        let review: Int?
        let changedExpired: Int?
        let items: [AvailabilityItem]?
        let current: Bool?
    }

    let configured: Bool?
    let trigger: Trigger?
    let latestRun: Run?
    let lastCompletedRun: Run?
    let results: Results?
}

struct AvailabilityItem: Codable, Identifiable, Hashable {
    let jobId: Int?
    let company: String?
    let role: String?
    let page: String?
    let url: String?
    let state: String?
    let reason: String?
    let checkedAt: String?
    let reviewType: String?
    let pendingNew: Bool?
    let source: String?

    var id: String { "\(jobId ?? 0)-\(page ?? role ?? "review")" }

    enum CodingKeys: String, CodingKey {
        case jobId = "id"
        case company, role, page, url, state, reason, checkedAt, reviewType, pendingNew, source
    }
}

struct PublishResponse: Decodable {
    let ok: Bool?
    let queued: Bool?
    let count: Int?
    let message: String?
}

struct ReviewResponse: Decodable {
    let ok: Bool?
    let action: String?
    let jobId: Int?
    let company: String?
    let role: String?
    let status: String?
    let results: AvailabilityResponse.Results?
    let message: String?
}

struct CheckerTriggerResponse: Decodable {
    let ok: Bool?
    let queued: Bool?
    let requestedAt: String?
    let commitSha: String?
    let message: String?
}

struct ExtractionEnvelope: Decodable {
    let ok: Bool?
    let data: Job?
    let error: String?
}

struct SessionResponse: Decodable {
    let ok: Bool?
    let authenticated: Bool?
    let error: String?
}

struct ErrorPayload: Decodable {
    let error: String?
}
