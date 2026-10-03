import Foundation

enum APIClientError: LocalizedError {
    case invalidResponse
    case server(String)
    case decoding(String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "The server returned an invalid response."
        case .server(let message):
            return message
        case .decoding(let message):
            return "Could not read the server response: \(message)"
        }
    }
}

final class APIClient {
    static let shared = APIClient()
    private let baseURL = URL(string: "https://hdcareers.in")!
    private let session: URLSession
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    private init() {
        let config = URLSessionConfiguration.default
        config.httpShouldSetCookies = true
        config.httpCookieStorage = .shared
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        config.timeoutIntervalForRequest = 45
        config.timeoutIntervalForResource = 90
        session = URLSession(configuration: config)
    }

    private func request<T: Decodable>(
        _ path: String,
        method: String = "GET",
        body: Data? = nil
    ) async throws -> T {
        guard let url = URL(string: path, relativeTo: baseURL) else {
            throw APIClientError.server("Invalid HD Careers API URL.")
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.httpBody = body
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if body != nil {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIClientError.invalidResponse
        }

        guard (200...299).contains(http.statusCode) else {
            if let payload = try? decoder.decode(ErrorPayload.self, from: data),
               let message = payload.error,
               !message.isEmpty {
                throw APIClientError.server(message)
            }
            throw APIClientError.server("HD Careers returned HTTP \(http.statusCode).")
        }

        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIClientError.decoding(error.localizedDescription)
        }
    }

    func sessionStatus() async throws -> Bool {
        let response: SessionResponse = try await request("/api/admin/session")
        return response.authenticated == true
    }

    func login(username: String, password: String) async throws {
        struct Body: Encodable { let username: String; let password: String }
        let data = try encoder.encode(Body(username: username, password: password))
        let response: SessionResponse = try await request("/api/admin/login", method: "POST", body: data)
        guard response.authenticated == true else {
            throw APIClientError.server(response.error ?? "Sign in failed.")
        }
    }

    func logout() async {
        struct Empty: Decodable {}
        _ = try? await request("/api/admin/logout", method: "POST", body: Data("{}".utf8)) as Empty
        if let cookies = HTTPCookieStorage.shared.cookies(for: baseURL) {
            for cookie in cookies {
                HTTPCookieStorage.shared.deleteCookie(cookie)
            }
        }
    }

    func jobs() async throws -> [Job] {
        try await request("/data/jobs.json")
    }

    func traffic(days: Int) async throws -> TrafficResponse {
        try await request("/api/admin/traffic?days=\(days)")
    }

    func automationHealth() async throws -> AutomationHealth {
        let url = URL(string: "https://raw.githubusercontent.com/Chethan-Mns/Hdcareers/preview/careers-favicon-logo-system/data/automation-status.json")!
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIClientError.invalidResponse
        }
        guard (200...299).contains(http.statusCode) else {
            throw APIClientError.server("Preview automation status returned HTTP \(http.statusCode).")
        }
        do {
            return try decoder.decode(AutomationHealth.self, from: data)
        } catch {
            throw APIClientError.decoding(error.localizedDescription)
        }
    }

    func availability() async throws -> AvailabilityResponse {
        try await request("/api/admin/availability")
    }

    func runChecker() async throws -> CheckerTriggerResponse {
        try await request("/api/admin/availability", method: "POST", body: Data("{}".utf8))
    }

    func resolveReview(jobId: Int, action: String) async throws -> ReviewResponse {
        struct Body: Encodable { let jobId: Int; let action: String }
        let data = try encoder.encode(Body(jobId: jobId, action: action))
        return try await request("/api/admin/review", method: "POST", body: data)
    }

    func extractJob(url: String) async throws -> Job {
        struct Body: Encodable { let url: String }
        let data = try encoder.encode(Body(url: url))
        let response: ExtractionEnvelope = try await request("/api/admin/extract-job", method: "POST", body: data)
        guard let job = response.data else {
            throw APIClientError.server(response.error ?? "Could not generate this job.")
        }
        return job
    }

    func publish(jobs: [Job]) async throws -> PublishResponse {
        struct Body: Encodable { let jobs: [Job] }
        let data = try encoder.encode(Body(jobs: jobs))
        return try await request("/api/admin/publish", method: "POST", body: data)
    }
}
