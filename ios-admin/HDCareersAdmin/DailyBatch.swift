import Foundation

struct DailyBatch: Codable {
    var batchId: String
    var generatedAt: String?
    var status: String
    var priority: [ReviewCandidate]
    var backup: [ReviewCandidate]
    var updatedAt: String?

    var isReady: Bool { !batchId.isEmpty && priority.count == 10 }
    var reviewedCount: Int { (priority + backup).filter { $0.reviewedStatus != nil && $0.reviewedStatus != "unreviewed" }.count }
    var readyToPublish: Bool {
        isReady && status != "submitted" && status != "published" &&
        priority.allSatisfy { $0.reviewedStatus == "live" && $0.isComplete }
    }
}

struct ReviewCandidate: Codable, Identifiable, Hashable {
    var id: String
    var company: String
    var role: String
    var loc: String?
    var cat: String?
    var apply: String?
    var expYears: String?
    var reviewedStatus: String?
    var verification: String?
    var reviewedAt: String?
    var reviewedBy: String?
    var job: Job?

    var officialURL: URL? {
        guard let value = apply ?? job?.apply, let url = URL(string: value), url.scheme == "https" else { return nil }
        return url
    }

    var categoryLabel: String {
        switch (cat ?? job?.cat ?? "it").lowercased() {
        case "nonit": return "Non-IT"
        case "internship": return "Internship"
        case "apprenticeship": return "Apprenticeship"
        default: return "Fresher IT"
        }
    }

    var isComplete: Bool {
        guard let job,
              !(job.company ?? "").isEmpty,
              !(job.role ?? "").isEmpty,
              !(job.loc ?? "").isEmpty,
              !(job.elig ?? "").isEmpty,
              !(job.desc ?? "").isEmpty,
              !(job.apply ?? "").isEmpty,
              !(job.resp ?? []).isEmpty else { return false }
        return true
    }
}