import SwiftUI

private func numberText(_ value: Int?) -> String {
    NumberFormatter.localizedString(from: NSNumber(value: value ?? 0), number: .decimal)
}

private func formatAdminDate(_ value: String?) -> String {
    guard let value, !value.isEmpty else { return "Never" }
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    var date = formatter.date(from: value)
    if date == nil {
        formatter.formatOptions = [.withInternetDateTime]
        date = formatter.date(from: value)
    }
    guard let date else { return value }

    let display = DateFormatter()
    display.locale = Locale(identifier: "en_IN")
    display.timeZone = TimeZone(identifier: "Asia/Kolkata")
    display.dateFormat = "dd MMM yyyy, h:mm a"
    return display.string(from: date)
}

private func siteURL(_ path: String?) -> URL? {
    guard let path, !path.isEmpty else { return nil }
    if let absolute = URL(string: path), absolute.scheme != nil { return absolute }
    return URL(string: "https://hdcareers.in/" + path.trimmingCharacters(in: CharacterSet(charactersIn: "/")))
}

private func jobDisplayName(path: String?, jobs: [Job]) -> String {
    guard let path else { return "HD Careers Home" }
    if path == "/" || path == "/index.html" { return "HD Careers Home" }
    let normalized = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
    if let job = jobs.first(where: { ($0.page ?? "").trimmingCharacters(in: CharacterSet(charactersIn: "/")) == normalized }) {
        return "\(job.company ?? "Job") — \(job.role ?? "Opening")"
    }
    return normalized
        .replacingOccurrences(of: "jobs/", with: "")
        .replacingOccurrences(of: ".html", with: "")
        .replacingOccurrences(of: "-", with: " ")
        .capitalized
}

struct LoginView: View {
    @EnvironmentObject private var state: AppState
    @State private var username = ""
    @State private var password = ""
    @State private var rememberWithFaceID = true

    private var canUseFaceID: Bool {
        BiometricAuth.isAvailable
    }

    private var hasSavedCredential: Bool {
        CredentialVault.load() != nil
    }

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [.white, HDTheme.background, HDTheme.blue.opacity(0.08)],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            ScrollView {
                VStack(spacing: 28) {
                    Spacer(minLength: 64)

                    VStack(spacing: 14) {
                        HDLogoView(size: 92)
                        Text("HD Careers Admin")
                            .font(.system(size: 28, weight: .black, design: .rounded))
                            .foregroundStyle(HDTheme.navy)
                        Text("Private control center for jobs, automations and analytics.")
                            .font(.subheadline)
                            .multilineTextAlignment(.center)
                            .foregroundStyle(.secondary)
                            .padding(.horizontal)
                    }

                    VStack(spacing: 14) {
                        HStack {
                            Image(systemName: "person.fill")
                                .foregroundStyle(.secondary)
                            TextField("Admin username", text: $username)
                                .textInputAutocapitalization(.never)
                                .autocorrectionDisabled()
                                .textContentType(.username)
                        }
                        .padding()
                        .background(Color.white)
                        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                        .overlay {
                            RoundedRectangle(cornerRadius: 16, style: .continuous)
                                .stroke(Color.black.opacity(0.08))
                        }

                        HStack {
                            Image(systemName: "lock.fill")
                                .foregroundStyle(.secondary)
                            SecureField("Password", text: $password)
                                .textContentType(.password)
                        }
                        .padding()
                        .background(Color.white)
                        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                        .overlay {
                            RoundedRectangle(cornerRadius: 16, style: .continuous)
                                .stroke(Color.black.opacity(0.08))
                        }

                        if canUseFaceID {
                            Toggle(isOn: $rememberWithFaceID) {
                                Label("Enable Face ID on this iPhone", systemImage: "faceid")
                                    .font(.footnote.weight(.semibold))
                            }
                            .tint(HDTheme.blue)
                        }

                        Button {
                            Task {
                                await state.login(
                                    username: username,
                                    password: password,
                                    rememberWithFaceID: rememberWithFaceID
                                )
                            }
                        } label: {
                            HStack {
                                if state.isBusy {
                                    ProgressView().tint(.white)
                                }
                                Text(state.isBusy ? "Signing in…" : "Sign In")
                                    .fontWeight(.bold)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 15)
                        }
                        .buttonStyle(.plain)
                        .foregroundStyle(.white)
                        .background(HDTheme.blue)
                        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                        .disabled(state.isBusy)

                        if canUseFaceID && hasSavedCredential {
                            Button {
                                Task { await state.faceIDLogin() }
                            } label: {
                                Label("Unlock with Face ID", systemImage: "faceid")
                                    .fontWeight(.bold)
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 14)
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(HDTheme.blue)
                            .background(HDTheme.blue.opacity(0.08))
                            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                        }
                    }
                    .hdCard(18)

                    Label("Private Admin Access", systemImage: "lock.shield")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)

                    Spacer(minLength: 30)
                }
                .padding(.horizontal, 20)
            }
        }
    }
}

struct RootTabView: View {
    @EnvironmentObject private var state: AppState
    @State private var selection = 0

    var body: some View {
        TabView(selection: $selection) {
            DashboardView()
                .tabItem { Label("Dashboard", systemImage: "house.fill") }
                .tag(0)

            JobsView()
                .tabItem { Label("Jobs", systemImage: "briefcase.fill") }
                .tag(1)

            PublishView()
                .tabItem { Label("Publish", systemImage: "wand.and.stars") }
                .tag(2)

            CheckerView()
                .tabItem { Label("Checker", systemImage: "checkmark.shield.fill") }
                .tag(3)

            MoreView()
                .tabItem { Label("More", systemImage: "ellipsis") }
                .tag(4)
        }
        .tint(HDTheme.blue)
        .task {
            if state.jobs.isEmpty {
                await state.refreshAll()
            }
        }
    }
}

struct AdminHeader: View {
    let title: String
    var subtitle: String? = nil
    var trailingSystemImage: String? = nil
    var trailingAction: (() -> Void)? = nil

    var body: some View {
        HStack(spacing: 12) {
            HDLogoView(size: 42)
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.headline.weight(.black))
                    .foregroundStyle(HDTheme.navy)
                if let subtitle {
                    Text(subtitle)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Spacer()
            if let trailingSystemImage, let trailingAction {
                Button(action: trailingAction) {
                    Image(systemName: trailingSystemImage)
                        .font(.system(size: 16, weight: .bold))
                        .frame(width: 38, height: 38)
                        .background(HDTheme.blue.opacity(0.08))
                        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
                }
                .buttonStyle(.plain)
            }
        }
    }
}

struct DashboardView: View {
    @EnvironmentObject private var state: AppState
    private let columns = [GridItem(.flexible()), GridItem(.flexible())]

    var body: some View {
        NavigationStack {
            ZStack {
                HDTheme.background.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 16) {
                        AdminHeader(
                            title: "HD Careers Admin",
                            subtitle: "Welcome back, Chethan",
                            trailingSystemImage: "arrow.clockwise"
                        ) {
                            Task { await state.refreshAll() }
                        }

                        LazyVGrid(columns: columns, spacing: 12) {
                            MetricTile(title: "Total Jobs", value: state.jobs.count, icon: "briefcase.fill", color: HDTheme.blue)
                            MetricTile(title: "Active", value: state.activeJobs.count, icon: "checkmark.circle.fill", color: HDTheme.green)
                            MetricTile(title: "Expired", value: state.expiredJobs.count, icon: "xmark.circle.fill", color: HDTheme.red)
                            MetricTile(title: "Freshers", value: state.fresherJobs.count, icon: "person.crop.circle.badge.checkmark", color: .purple)
                        }

                        TrafficSummaryCard()
                        AutomationHealthCard()
                    }
                    .padding(16)
                    .padding(.bottom, 14)
                }
                .refreshable { await state.refreshAll() }
            }
            .toolbar(.hidden, for: .navigationBar)
        }
    }
}

struct MetricTile: View {
    let title: String
    let value: Int
    let icon: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Image(systemName: icon)
                    .foregroundStyle(color)
                Spacer()
            }
            Text(numberText(value))
                .font(.system(size: 28, weight: .black, design: .rounded))
                .foregroundStyle(HDTheme.navy)
            Text(title)
                .font(.caption.weight(.bold))
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .hdCard(14)
    }
}

struct TrafficSummaryCard: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Website Traffic")
                        .font(.headline.weight(.black))
                    Text("Live GA4 data")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                StatusPill(text: "Live", color: HDTheme.green, icon: "circle.fill")
            }

            Picker("Period", selection: Binding(
                get: { state.trafficDays },
                set: { days in Task { await state.loadTraffic(days: days) } }
            )) {
                Text("24H").tag(1)
                Text("7D").tag(7)
                Text("30D").tag(30)
            }
            .pickerStyle(.segmented)

            HStack(spacing: 10) {
                SmallMetric(title: "Live now", value: state.traffic?.realtimeUsers ?? 0, color: HDTheme.green)
                SmallMetric(title: "Users", value: state.traffic?.totals?.visitors ?? 0, color: HDTheme.blue)
                SmallMetric(title: "Views", value: state.traffic?.totals?.pageviews ?? 0, color: .purple)
            }

            if let page = state.traffic?.pages?.first {
                Divider()
                Text("Top page")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.secondary)
                if let url = siteURL(page.requestPath) {
                    Link(destination: url) {
                        HStack {
                            Text(jobDisplayName(path: page.requestPath, jobs: state.jobs))
                                .font(.subheadline.weight(.semibold))
                                .lineLimit(2)
                            Spacer()
                            Image(systemName: "arrow.up.right")
                        }
                    }
                }
            }
        }
        .hdCard()
    }
}

struct SmallMetric: View {
    let title: String
    let value: Int
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(numberText(value))
                .font(.title3.weight(.black))
                .foregroundStyle(HDTheme.navy)
            Text(title)
                .font(.caption2.weight(.bold))
                .foregroundStyle(color)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(11)
        .background(color.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}

struct AutomationHealthCard: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 13) {
            HStack {
                Text("Automation Health")
                    .font(.headline.weight(.black))
                Spacer()
                if let slots = state.automationHealth?.slots {
                    StatusPill(
                        text: "\(slots.filter(\.enabled).count)/\(slots.count) running",
                        color: HDTheme.green,
                        icon: "bolt.fill"
                    )
                }
            }

            if let slots = state.automationHealth?.slots, !slots.isEmpty {
                ForEach(slots) { slot in
                    AutomationRow(slot: slot)
                    if slot.id != slots.last?.id {
                        Divider()
                    }
                }
            } else {
                Text("Automation status will appear after refresh.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .hdCard()
    }
}

struct AutomationRow: View {
    let slot: AutomationHealth.Slot

    private var outcomeColor: Color {
        switch slot.outcome {
        case "published": return HDTheme.green
        case "error": return HDTheme.red
        case "no_publish": return HDTheme.amber
        default: return HDTheme.blue
        }
    }

    var body: some View {
        HStack(spacing: 10) {
            Circle()
                .fill(slot.enabled ? outcomeColor : Color.gray)
                .frame(width: 9, height: 9)
            VStack(alignment: .leading, spacing: 2) {
                Text("\(slot.time) · \(slot.title)")
                    .font(.subheadline.weight(.bold))
                Text(slot.lastRunAt.map { "Last: \(formatAdminDate($0))" } ?? "Next scheduled run")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer()
            if let outcome = slot.outcome {
                StatusPill(text: outcome.replacingOccurrences(of: "_", with: " ").capitalized, color: outcomeColor)
            }
        }
    }
}

enum JobListFilter: String, CaseIterable, Identifiable {
    case all = "All"
    case active = "Active"
    case expired = "Expired"
    var id: String { rawValue }
}

struct JobsView: View {
    @EnvironmentObject private var state: AppState
    @State private var search = ""
    @State private var filter: JobListFilter = .all

    private var filteredJobs: [Job] {
        state.jobs.filter { job in
            let matchesFilter: Bool
            switch filter {
            case .all: matchesFilter = true
            case .active: matchesFilter = job.isActive
            case .expired: matchesFilter = job.isExpired
            }

            guard matchesFilter else { return false }
            guard !search.isEmpty else { return true }
            let haystack = [job.company, job.role, job.loc, job.cat].compactMap { $0 }.joined(separator: " ").lowercased()
            return haystack.contains(search.lowercased())
        }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                HDTheme.background.ignoresSafeArea()
                ScrollView {
                    VStack(spacing: 14) {
                        AdminHeader(
                            title: "All Jobs",
                            subtitle: "\(state.jobs.count) published jobs",
                            trailingSystemImage: "arrow.clockwise"
                        ) {
                            Task { await state.refreshJobs() }
                        }

                        HStack {
                            Image(systemName: "magnifyingglass")
                                .foregroundStyle(.secondary)
                            TextField("Search title, company or location", text: $search)
                                .textInputAutocapitalization(.never)
                        }
                        .padding(12)
                        .background(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

                        Picker("Status", selection: $filter) {
                            ForEach(JobListFilter.allCases) { item in
                                Text("\(item.rawValue) \(count(for: item))").tag(item)
                            }
                        }
                        .pickerStyle(.segmented)

                        if filteredJobs.isEmpty {
                            EmptyState(icon: "briefcase", title: "No jobs found", message: "Try changing your search or status filter.")
                                .hdCard()
                        } else {
                            LazyVStack(spacing: 10) {
                                ForEach(filteredJobs) { job in
                                    JobRow(job: job)
                                }
                            }
                        }
                    }
                    .padding(16)
                    .padding(.bottom, 16)
                }
                .refreshable { await state.refreshJobs() }
            }
            .toolbar(.hidden, for: .navigationBar)
        }
    }

    private func count(for filter: JobListFilter) -> Int {
        switch filter {
        case .all: return state.jobs.count
        case .active: return state.activeJobs.count
        case .expired: return state.expiredJobs.count
        }
    }
}

struct JobRow: View {
    let job: Job

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(HDTheme.blue.opacity(0.10))
                .frame(width: 46, height: 46)
                .overlay {
                    Text(initials(job.company ?? "HD"))
                        .font(.caption.weight(.black))
                        .foregroundStyle(HDTheme.blue)
                }

            VStack(alignment: .leading, spacing: 5) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(job.company ?? "Company")
                            .font(.headline.weight(.black))
                        Text(job.role ?? "Job Opening")
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    }
                    Spacer(minLength: 8)
                    StatusPill(
                        text: job.isExpired ? "Expired" : "Active",
                        color: job.isExpired ? HDTheme.red : HDTheme.green
                    )
                }

                HStack(spacing: 8) {
                    Label(job.loc ?? "Not specified", systemImage: "mappin.and.ellipse")
                    Label(job.expType?.capitalized ?? "Job", systemImage: "person.fill")
                }
                .font(.caption2)
                .foregroundStyle(.secondary)
                .lineLimit(1)

                HStack(spacing: 12) {
                    if let site = job.siteURL {
                        Link("HD Careers", destination: site)
                    }
                    if let official = job.officialURL {
                        Link("Official ↗", destination: official)
                    }
                }
                .font(.caption.weight(.bold))
                .foregroundStyle(HDTheme.blue)
            }
        }
        .hdCard(14)
    }

    private func initials(_ company: String) -> String {
        let parts = company.split(separator: " ")
        if parts.count >= 2 {
            return (String(parts[0].prefix(1)) + String(parts[1].prefix(1))).uppercased()
        }
        return String(company.prefix(2)).uppercased()
    }
}

struct ParsedAdminLink: Identifiable {
    let lineIndex: Int
    let raw: String
    let url: URL?
    let duplicate: Bool

    var id: String { "\(lineIndex)-\(raw)" }
    var valid: Bool { url?.scheme == "https" && !(url?.host?.isEmpty ?? true) }
    var domain: String { url?.host?.replacingOccurrences(of: "www.", with: "") ?? "Invalid URL" }
    var path: String {
        guard let url else { return raw }
        let query = url.query.map { "?\($0)" } ?? ""
        return url.path + query
    }
}

struct EditSelection: Identifiable {
    let id: Int
}

struct PublishView: View {
    @EnvironmentObject private var state: AppState
    @State private var rawLinks = ""
    @State private var drafts: [Job] = []
    @State private var selectedIDs: Set<String> = []
    @State private var isGenerating = false
    @State private var processed = 0
    @State private var extractionIssues: [String] = []
    @State private var editSelection: EditSelection?
    @State private var showPublishConfirmation = false

    private var parsedLinks: [ParsedAdminLink] {
        let lines = rawLinks
            .split(whereSeparator: \.isNewline)
            .map { String($0).trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }

        var seen = Set<String>()
        return lines.enumerated().map { index, raw in
            let url = URL(string: raw)
            let normalized = url?.absoluteString.lowercased().trimmingCharacters(in: CharacterSet(charactersIn: "/")) ?? raw.lowercased()
            let duplicate = seen.contains(normalized)
            if url != nil && !duplicate { seen.insert(normalized) }
            return ParsedAdminLink(lineIndex: index, raw: raw, url: url, duplicate: duplicate)
        }
    }

    private var readyLinks: [ParsedAdminLink] {
        parsedLinks.filter { $0.valid && !$0.duplicate }
    }

    private var selectedDrafts: [Job] {
        drafts.filter { selectedIDs.contains($0.id) }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                HDTheme.background.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 16) {
                        AdminHeader(title: "Add / Publish Jobs", subtitle: "Private publishing workflow")

                        VStack(alignment: .leading, spacing: 13) {
                            HStack {
                                Label("Paste Official Job Links", systemImage: "link")
                                    .font(.headline.weight(.black))
                                Spacer()
                                StatusPill(
                                    text: "\(readyLinks.count) ready",
                                    color: readyLinks.isEmpty ? Color.gray : HDTheme.green,
                                    icon: readyLinks.isEmpty ? "link" : "checkmark.circle.fill"
                                )
                            }

                            Text("Paste up to 20 official employer URLs, one per line.")
                                .font(.caption)
                                .foregroundStyle(.secondary)

                            TextEditor(text: $rawLinks)
                                .frame(minHeight: 120)
                                .padding(9)
                                .scrollContentBackground(.hidden)
                                .background(Color(.secondarySystemBackground))
                                .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))

                            if parsedLinks.isEmpty {
                                EmptyState(icon: "link", title: "No links yet", message: "Paste official job URLs above to preview them.")
                                    .padding(.vertical, -6)
                            } else {
                                VStack(spacing: 8) {
                                    ForEach(parsedLinks) { item in
                                        LinkPreviewRow(item: item) {
                                            removeLink(at: item.lineIndex)
                                        }
                                    }
                                }
                            }

                            Button {
                                Task { await generateJobs() }
                            } label: {
                                HStack {
                                    if isGenerating {
                                        ProgressView().tint(.white)
                                    } else {
                                        Image(systemName: "wand.and.stars")
                                    }
                                    Text(isGenerating ? "Generating \(processed)/\(readyLinks.count)…" : "Generate \(readyLinks.count) job\(readyLinks.count == 1 ? "" : "s")")
                                        .fontWeight(.bold)
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(.white)
                            .background(readyLinks.isEmpty || isGenerating ? Color.gray.opacity(0.5) : HDTheme.blue)
                            .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
                            .disabled(readyLinks.isEmpty || isGenerating)
                        }
                        .hdCard()

                        if !extractionIssues.isEmpty {
                            VStack(alignment: .leading, spacing: 8) {
                                Label("Extraction issues", systemImage: "exclamationmark.triangle.fill")
                                    .font(.headline)
                                    .foregroundStyle(HDTheme.amber)
                                ForEach(extractionIssues, id: \.self) { issue in
                                    Text("• \(issue)")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .hdCard()
                        }

                        if !drafts.isEmpty {
                            VStack(alignment: .leading, spacing: 12) {
                                HStack {
                                    Text("Generated Preview")
                                        .font(.headline.weight(.black))
                                    Spacer()
                                    Text("\(selectedDrafts.count) selected")
                                        .font(.caption.weight(.bold))
                                        .foregroundStyle(.secondary)
                                }

                                ForEach(Array(drafts.enumerated()), id: \.element.id) { index, job in
                                    DraftJobRow(
                                        job: job,
                                        selected: selectedIDs.contains(job.id),
                                        toggle: {
                                            if selectedIDs.contains(job.id) {
                                                selectedIDs.remove(job.id)
                                            } else {
                                                selectedIDs.insert(job.id)
                                            }
                                        },
                                        edit: { editSelection = EditSelection(id: index) }
                                    )
                                }

                                Button {
                                    showPublishConfirmation = true
                                } label: {
                                    Label(
                                        "Publish \(selectedDrafts.count) to HD Careers",
                                        systemImage: "arrow.up.circle.fill"
                                    )
                                    .fontWeight(.bold)
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 14)
                                }
                                .buttonStyle(.plain)
                                .foregroundStyle(.white)
                                .background(selectedDrafts.isEmpty ? Color.gray.opacity(0.5) : HDTheme.blue)
                                .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
                                .disabled(selectedDrafts.isEmpty || state.isBusy)
                            }
                            .hdCard()
                        }
                    }
                    .padding(16)
                    .padding(.bottom, 18)
                }
            }
            .toolbar(.hidden, for: .navigationBar)
            .sheet(item: $editSelection) { selection in
                if drafts.indices.contains(selection.id) {
                    JobEditSheet(job: Binding(
                        get: { drafts[selection.id] },
                        set: { drafts[selection.id] = $0 }
                    ))
                }
            }
            .confirmationDialog(
                "Publish selected jobs?",
                isPresented: $showPublishConfirmation,
                titleVisibility: .visible
            ) {
                Button("Publish \(selectedDrafts.count) jobs") {
                    Task { await publishSelected() }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("The existing HD Careers validation, generation, Vercel deployment and Telegram workflow will run.")
            }
        }
    }

    private func removeLink(at index: Int) {
        var lines = rawLinks
            .split(whereSeparator: \.isNewline)
            .map(String.init)
            .filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }

        guard lines.indices.contains(index) else { return }
        lines.remove(at: index)
        rawLinks = lines.joined(separator: "\n")
    }

    private func generateJobs() async {
        let links = readyLinks
        guard !links.isEmpty else { return }
        guard links.count <= 20 else {
            state.alertMessage = "Maximum 20 job links per batch."
            return
        }

        isGenerating = true
        processed = 0
        extractionIssues = []
        drafts = []
        selectedIDs = []

        var generated: [(Int, Job)] = []
        var issues: [String] = []

        for start in stride(from: 0, to: links.count, by: 3) {
            let end = min(start + 3, links.count)
            let batch = Array(links[start..<end])

            await withTaskGroup(of: (Int, Job?, String?).self) { group in
                for (offset, link) in batch.enumerated() {
                    let index = start + offset
                    group.addTask {
                        do {
                            let job = try await APIClient.shared.extractJob(url: link.raw)
                            return (index, job, nil)
                        } catch {
                            return (index, nil, "\(link.domain): \(error.localizedDescription)")
                        }
                    }
                }

                for await result in group {
                    processed += 1
                    if let job = result.1 {
                        generated.append((result.0, job))
                    }
                    if let issue = result.2 {
                        issues.append(issue)
                    }
                }
            }
        }

        drafts = generated.sorted { $0.0 < $1.0 }.map(\.1)
        selectedIDs = Set(drafts.map(\.id))
        extractionIssues = issues
        isGenerating = false
    }

    private func publishSelected() async {
        let jobs = selectedDrafts
        guard !jobs.isEmpty else { return }

        state.isBusy = true
        defer { state.isBusy = false }

        do {
            let response = try await state.api.publish(jobs: jobs)
            state.alertMessage = response.message ?? "Production deployment started."
            rawLinks = ""
            drafts = []
            selectedIDs = []
            extractionIssues = []
            try? await Task.sleep(for: .seconds(2))
            await state.refreshJobs()
        } catch {
            state.alertMessage = error.localizedDescription
        }
    }
}

struct LinkPreviewRow: View {
    let item: ParsedAdminLink
    let remove: () -> Void

    private var color: Color {
        if !item.valid { return HDTheme.red }
        if item.duplicate { return HDTheme.amber }
        return HDTheme.green
    }

    private var status: String {
        if !item.valid { return "Invalid" }
        if item.duplicate { return "Duplicate" }
        return "Ready"
    }

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: item.valid ? "link" : "exclamationmark.triangle.fill")
                .foregroundStyle(color)
                .frame(width: 34, height: 34)
                .background(color.opacity(0.10))
                .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))

            VStack(alignment: .leading, spacing: 3) {
                HStack {
                    Text(item.domain)
                        .font(.subheadline.weight(.black))
                        .lineLimit(1)
                    StatusPill(text: status, color: color)
                }
                Text(item.path)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(2)
            }

            Spacer(minLength: 4)

            HStack(spacing: 8) {
                if let url = item.url, item.valid {
                    Link(destination: url) {
                        Image(systemName: "arrow.up.right")
                    }
                }
                Button(action: remove) {
                    Image(systemName: "xmark")
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
            }
            .font(.caption.weight(.bold))
        }
        .padding(10)
        .background(color.opacity(0.035))
        .clipShape(RoundedRectangle(cornerRadius: 13, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 13, style: .continuous)
                .stroke(color.opacity(0.18))
        }
    }
}

struct DraftJobRow: View {
    let job: Job
    let selected: Bool
    let toggle: () -> Void
    let edit: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Button(action: toggle) {
                Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(selected ? HDTheme.blue : .secondary)
                    .font(.title3)
            }
            .buttonStyle(.plain)

            VStack(alignment: .leading, spacing: 4) {
                Text(job.company ?? "Company")
                    .font(.headline.weight(.black))
                Text(job.role ?? "Job Opening")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.secondary)
                HStack {
                    StatusPill(text: job.cat?.capitalized ?? "Job", color: HDTheme.blue)
                    Text(job.loc ?? "Location not specified")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }

            Spacer()

            Button(action: edit) {
                Image(systemName: "pencil")
                    .font(.caption.weight(.bold))
                    .padding(9)
                    .background(HDTheme.blue.opacity(0.08))
                    .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
            }
            .buttonStyle(.plain)
        }
        .padding(12)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }
}

struct JobEditSheet: View {
    @Environment(\.dismiss) private var dismiss
    @Binding var job: Job

    private func binding(_ keyPath: WritableKeyPath<Job, String?>) -> Binding<String> {
        Binding(
            get: { job[keyPath: keyPath] ?? "" },
            set: { job[keyPath: keyPath] = $0 }
        )
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Basics") {
                    TextField("Company", text: binding(\.company))
                    TextField("Role", text: binding(\.role))
                    TextField("Location", text: binding(\.loc))
                    TextField("Experience", text: binding(\.expYears))
                    TextField("Batch", text: binding(\.batch))
                    TextField("Salary", text: binding(\.salary))
                }

                Section("Official source") {
                    TextField("Official URL", text: binding(\.apply))
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    TextField("Source name", text: binding(\.sourceName))
                }

                Section("Eligibility") {
                    TextEditor(text: binding(\.elig))
                        .frame(minHeight: 110)
                }

                Section("Description") {
                    TextEditor(text: binding(\.desc))
                        .frame(minHeight: 150)
                }
            }
            .navigationTitle("Edit Job")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                        .fontWeight(.bold)
                }
            }
        }
    }
}

struct CheckerView: View {
    @EnvironmentObject private var state: AppState
    @State private var pendingRemove: AvailabilityItem?

    private var results: AvailabilityResponse.Results? {
        state.availability?.results
    }

    private var reviewItems: [AvailabilityItem] {
        results?.items?.filter { $0.state == "review" } ?? []
    }

    var body: some View {
        NavigationStack {
            ZStack {
                HDTheme.background.ignoresSafeArea()
                ScrollView {
                    VStack(spacing: 16) {
                        AdminHeader(
                            title: "Expired Job Checker",
                            subtitle: "Conservative official-link verification",
                            trailingSystemImage: "arrow.clockwise"
                        ) {
                            Task { await state.refreshChecker() }
                        }

                        VStack(alignment: .leading, spacing: 14) {
                            HStack {
                                VStack(alignment: .leading, spacing: 3) {
                                    Text("Last Run")
                                        .font(.caption.weight(.bold))
                                        .foregroundStyle(.secondary)
                                    Text(formatAdminDate(results?.checkedAt))
                                        .font(.subheadline.weight(.black))
                                }
                                Spacer()
                                StatusPill(
                                    text: state.availability?.latestRun?.status?.capitalized ?? "Saved",
                                    color: HDTheme.green,
                                    icon: "checkmark.circle.fill"
                                )
                            }

                            HStack(spacing: 10) {
                                SmallMetric(title: "Expired", value: results?.expired ?? 0, color: HDTheme.red)
                                SmallMetric(title: "Needs Review", value: results?.review ?? 0, color: HDTheme.amber)
                                SmallMetric(title: "No Change", value: results?.active ?? 0, color: HDTheme.green)
                            }

                            Button {
                                Task { await state.runChecker() }
                            } label: {
                                HStack {
                                    if state.isBusy { ProgressView().tint(.white) }
                                    Image(systemName: "play.fill")
                                    Text("Run Checker Now").fontWeight(.bold)
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 14)
                            }
                            .buttonStyle(.plain)
                            .foregroundStyle(.white)
                            .background(HDTheme.amber)
                            .clipShape(RoundedRectangle(cornerRadius: 15, style: .continuous))
                            .disabled(state.isBusy)
                        }
                        .hdCard()

                        if reviewItems.isEmpty {
                            VStack(spacing: 8) {
                                Image(systemName: "checkmark.shield.fill")
                                    .font(.system(size: 30))
                                    .foregroundStyle(HDTheme.green)
                                Text("No jobs need review")
                                    .font(.headline.weight(.black))
                                Text("The current checker result has no unresolved review items.")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                                    .multilineTextAlignment(.center)
                            }
                            .frame(maxWidth: .infinity)
                            .hdCard()
                        } else {
                            VStack(alignment: .leading, spacing: 12) {
                                Text("Needs Review (\(reviewItems.count))")
                                    .font(.headline.weight(.black))

                                ForEach(reviewItems) { item in
                                    ReviewItemCard(
                                        item: item,
                                        remove: { pendingRemove = item },
                                        keep: {
                                            Task { await state.resolveReview(item, action: "keep") }
                                        }
                                    )
                                }
                            }
                        }
                    }
                    .padding(16)
                    .padding(.bottom, 16)
                }
                .refreshable { await state.refreshChecker() }
            }
            .toolbar(.hidden, for: .navigationBar)
            .confirmationDialog(
                "Mark this job expired?",
                isPresented: Binding(
                    get: { pendingRemove != nil },
                    set: { if !$0 { pendingRemove = nil } }
                ),
                titleVisibility: .visible
            ) {
                Button("Remove / Mark Expired", role: .destructive) {
                    if let item = pendingRemove {
                        Task { await state.resolveReview(item, action: "expire") }
                    }
                    pendingRemove = nil
                }
                Button("Cancel", role: .cancel) { pendingRemove = nil }
            } message: {
                Text("This will mark the job expired in HD Careers and trigger the normal website regeneration.")
            }
        }
    }
}

struct ReviewItemCard: View {
    let item: AvailabilityItem
    let remove: () -> Void
    let keep: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 3) {
                    Text(item.company ?? "Company")
                        .font(.headline.weight(.black))
                    Text(item.role ?? "Job Opening")
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.secondary)
                }
                Spacer()
                StatusPill(text: "Needs Review", color: HDTheme.amber)
            }

            Text(item.reason ?? "Availability could not be confirmed.")
                .font(.caption)
                .foregroundStyle(.secondary)

            HStack(spacing: 8) {
                if let official = item.url.flatMap(URL.init(string:)) {
                    Link(destination: official) {
                        Label("Official", systemImage: "arrow.up.right.square")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                }

                if let hd = siteURL(item.page) {
                    Link(destination: hd) {
                        Label("HD Careers", systemImage: "eye")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                }
            }

            HStack(spacing: 8) {
                Button(role: .destructive, action: remove) {
                    Label("Remove", systemImage: "trash.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)

                Button(action: keep) {
                    Label("No Change", systemImage: "checkmark")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(HDTheme.green)
            }
        }
        .hdCard(14)
    }
}

struct MoreView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        NavigationStack {
            ZStack {
                HDTheme.background.ignoresSafeArea()
                ScrollView {
                    VStack(spacing: 16) {
                        AdminHeader(title: "More", subtitle: "HD Careers Admin")

                        HStack(spacing: 14) {
                            Circle()
                                .fill(HDTheme.blue.opacity(0.12))
                                .frame(width: 58, height: 58)
                                .overlay {
                                    Text("C")
                                        .font(.title2.weight(.black))
                                        .foregroundStyle(HDTheme.blue)
                                }
                            VStack(alignment: .leading, spacing: 3) {
                                Text("Chethan")
                                    .font(.title3.weight(.black))
                                Text("Private administrator")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                        }
                        .hdCard()

                        VStack(spacing: 0) {
                            NavigationLink {
                                AnalyticsView()
                            } label: {
                                MoreRow(icon: "chart.bar.fill", title: "Website Analytics", color: HDTheme.blue)
                            }
                            Divider().padding(.leading, 48)
                            NavigationLink {
                                AutomationDetailsView()
                            } label: {
                                MoreRow(icon: "bolt.horizontal.circle.fill", title: "Automation Health", color: HDTheme.green)
                            }
                            Divider().padding(.leading, 48)
                            if let adminURL = URL(string: "https://hdcareers.in/admin/") {
                                Link(destination: adminURL) {
                                    MoreRow(icon: "safari.fill", title: "Open Web Admin", color: .purple)
                                }
                            }
                            Divider().padding(.leading, 48)
                            if let site = URL(string: "https://hdcareers.in") {
                                Link(destination: site) {
                                    MoreRow(icon: "globe", title: "Open HD Careers", color: HDTheme.blue)
                                }
                            }
                        }
                        .hdCard(0)

                        if CredentialVault.load() != nil {
                            Button(role: .destructive) {
                                state.removeSavedFaceID()
                            } label: {
                                Label("Remove saved Face ID login", systemImage: "faceid")
                                    .fontWeight(.semibold)
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 13)
                            }
                            .buttonStyle(.bordered)
                        }

                        Button(role: .destructive) {
                            Task { await state.logout() }
                        } label: {
                            Label("Sign Out", systemImage: "rectangle.portrait.and.arrow.right")
                                .fontWeight(.bold)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 13)
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding(16)
                }
            }
            .toolbar(.hidden, for: .navigationBar)
        }
    }
}

struct MoreRow: View {
    let icon: String
    let title: String
    let color: Color

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundStyle(color)
                .frame(width: 26)
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(HDTheme.navy)
            Spacer()
            Image(systemName: "chevron.right")
                .font(.caption.weight(.bold))
                .foregroundStyle(.tertiary)
        }
        .padding(15)
        .contentShape(Rectangle())
    }
}

struct AnalyticsView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        ZStack {
            HDTheme.background.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 14) {
                    Picker("Period", selection: Binding(
                        get: { state.trafficDays },
                        set: { days in Task { await state.loadTraffic(days: days) } }
                    )) {
                        Text("24H").tag(1)
                        Text("7D").tag(7)
                        Text("30D").tag(30)
                    }
                    .pickerStyle(.segmented)

                    HStack(spacing: 10) {
                        SmallMetric(title: "Live now", value: state.traffic?.realtimeUsers ?? 0, color: HDTheme.green)
                        SmallMetric(title: "Users", value: state.traffic?.totals?.visitors ?? 0, color: HDTheme.blue)
                        SmallMetric(title: "Views", value: state.traffic?.totals?.pageviews ?? 0, color: .purple)
                    }
                    .hdCard(10)

                    AnalyticsListCard(
                        title: "Top Pages",
                        icon: "doc.text.fill",
                        rows: (state.traffic?.pages ?? []).map {
                            (jobDisplayName(path: $0.requestPath, jobs: state.jobs), $0.pageviews ?? 0)
                        }
                    )

                    AnalyticsListCard(
                        title: "Traffic Sources",
                        icon: "arrow.up.right.square.fill",
                        rows: (state.traffic?.referrers ?? []).map {
                            (($0.referrerHostname?.isEmpty == false ? $0.referrerHostname! : "Direct / Unknown"), $0.sessions ?? 0)
                        }
                    )

                    AnalyticsListCard(
                        title: "Countries",
                        icon: "globe.asia.australia.fill",
                        rows: (state.traffic?.countries ?? []).map {
                            ($0.country ?? "Unknown", $0.visitors ?? 0)
                        }
                    )

                    AnalyticsListCard(
                        title: "Devices",
                        icon: "iphone",
                        rows: (state.traffic?.devices ?? []).map {
                            (($0.deviceType ?? "Unknown").capitalized, $0.visitors ?? 0)
                        }
                    )
                }
                .padding(16)
            }
        }
        .navigationTitle("Analytics")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct AnalyticsListCard: View {
    let title: String
    let icon: String
    let rows: [(String, Int)]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(title, systemImage: icon)
                .font(.headline.weight(.black))

            if rows.isEmpty {
                Text("No data for this period.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(Array(rows.enumerated()), id: \.offset) { index, row in
                    HStack(alignment: .top) {
                        Text("\(index + 1)")
                            .font(.caption.weight(.black))
                            .foregroundStyle(HDTheme.blue)
                            .frame(width: 22, height: 22)
                            .background(HDTheme.blue.opacity(0.08))
                            .clipShape(Circle())
                        Text(row.0)
                            .font(.subheadline.weight(.semibold))
                            .lineLimit(2)
                        Spacer()
                        Text(numberText(row.1))
                            .font(.subheadline.weight(.black))
                    }
                    if index != rows.count - 1 {
                        Divider()
                    }
                }
            }
        }
        .hdCard()
    }
}

struct AutomationDetailsView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        ZStack {
            HDTheme.background.ignoresSafeArea()

            ScrollView {
                VStack(spacing: 12) {
                    if let slots = state.automationHealth?.slots {
                        ForEach(slots) { slot in
                            VStack(alignment: .leading, spacing: 10) {
                                HStack {
                                    Circle()
                                        .fill(slot.enabled ? HDTheme.green : Color.gray)
                                        .frame(width: 10, height: 10)
                                    Text("\(slot.time) — \(slot.title)")
                                        .font(.headline.weight(.black))
                                    Spacer()
                                    if let outcome = slot.outcome {
                                        StatusPill(
                                            text: outcome.replacingOccurrences(of: "_", with: " ").capitalized,
                                            color: outcome == "error" ? HDTheme.red : outcome == "no_publish" ? HDTheme.amber : HDTheme.green
                                        )
                                    }
                                }

                                Text("Last run: \(formatAdminDate(slot.lastRunAt))")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)

                                if let detail = slot.detail, !detail.isEmpty {
                                    Text(detail)
                                        .font(.subheadline)
                                        .foregroundStyle(.secondary)
                                }

                                if let page = siteURL(slot.page) {
                                    Link("Open published job ↗", destination: page)
                                        .font(.caption.weight(.bold))
                                }
                            }
                            .hdCard()
                        }
                    } else {
                        EmptyState(icon: "bolt.slash", title: "No automation status", message: "Refresh the dashboard to load automation health.")
                            .hdCard()
                    }
                }
                .padding(16)
            }
        }
        .navigationTitle("Automation Health")
        .navigationBarTitleDisplayMode(.inline)
    }
}
