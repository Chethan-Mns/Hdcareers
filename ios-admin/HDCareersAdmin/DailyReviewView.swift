import SwiftUI

struct DailyReviewView: View {
    @EnvironmentObject private var state: AppState
    @State private var selectedTab = 0
    @State private var confirmPublish = false

    private var batch: DailyBatch? { state.dailyBatch }

    var body: some View {
        NavigationStack {
            ZStack {
                HDTheme.background.ignoresSafeArea()
                ScrollView {
                    VStack(alignment: .leading, spacing: 15) {
                        AdminHeader(title: "Review jobs", subtitle: "10 priority + 10 backups",
                                    trailingSystemImage: "arrow.clockwise") {
                            Task { await state.refreshDailyBatch() }
                        }

                        headerCard

                        if let batch, !batch.batchId.isEmpty {
                            Picker("Review group", selection: $selectedTab) {
                                Text("Priority 10").tag(0)
                                Text("Backup 10").tag(1)
                            }
                            .pickerStyle(.segmented)
                            .accessibilityLabel("Choose priority or backup jobs")

                            Text(selectedTab == 0
                                 ? "Review each selected job before publishing. Replace expired roles with verified backup jobs."
                                 : "Verify backups as Live so they can replace an expired priority job.")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                                .fixedSize(horizontal: false, vertical: true)

                            ForEach(selectedTab == 0 ? batch.priority : batch.backup) { job in
                                DailyReviewCandidateCard(
                                    candidate: job,
                                    isPriority: selectedTab == 0,
                                    backups: batch.backup,
                                    isDisabled: state.isBatchBusy || batch.status == "submitted" || batch.status == "published",
                                    onDecision: { value in
                                        Task { await state.setDailyDecision(candidateId: job.id, decision: value) }
                                    },
                                    onReplace: { backup in
                                        Task { await state.swapDailyCandidate(priorityId: job.id, backupId: backup.id) }
                                    }
                                )
                            }

                            if selectedTab == 0 {
                                VStack(alignment: .leading, spacing: 12) {
                                    Text("Ready to publish?")
                                        .font(.headline)
                                    Text("All 10 priority jobs must be manually marked Live and include complete verified job content. Deployment and Telegram delivery are checked separately.")
                                        .font(.footnote)
                                        .foregroundStyle(.secondary)
                                        .fixedSize(horizontal: false, vertical: true)

                                    Button {
                                        confirmPublish = true
                                    } label: {
                                        HStack {
                                            Image(systemName: "paperplane.fill")
                                            Text(batch.status == "submitted" ? "Submitted to publisher" : "Publish reviewed 10 jobs")
                                        }
                                        .frame(maxWidth: .infinity)
                                        .padding(.vertical, 5)
                                    }
                                    .buttonStyle(.borderedProminent)
                                    .disabled(!batch.readyToPublish || state.isBatchBusy)
                                }
                                .premiumCard()
                            }
                        } else {
                            VStack(spacing: 12) {
                                Image(systemName: "tray.full.fill")
                                    .font(.system(size: 32))
                                    .foregroundStyle(HDTheme.blue)
                                Text("Waiting for the next discovery batch")
                                    .font(.headline)
                                Text("The 9 AM discovery workflow must save its ranked Priority 10 and Backup 10 here. No example jobs will be shown as real openings.")
                                    .font(.subheadline)
                                    .multilineTextAlignment(.center)
                                    .foregroundStyle(.secondary)
                                Button("Check again") { Task { await state.refreshDailyBatch() } }
                                    .buttonStyle(.bordered)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 28)
                            .premiumCard()
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 14)
                }
                .refreshable { await state.refreshDailyBatch() }
            }
            .toolbar(.hidden, for: .navigationBar)
            .alert("Publish these 10 jobs?", isPresented: $confirmPublish) {
                Button("Cancel", role: .cancel) {}
                Button("Submit batch") { Task { await state.publishDailyBatch() } }
            } message: {
                Text("This starts the existing website publishing workflow. Telegram posting follows successful deployment.")
            }
        }
        .task { await state.refreshDailyBatch() }
    }

    private var headerCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("DAILY APPROVAL CENTER")
                        .font(.caption2.weight(.heavy))
                        .tracking(1.1)
                        .foregroundStyle(.white.opacity(0.75))
                    Text(batch?.batchId.isEmpty == false ? "Today's shortlist" : "Ready for the next batch")
                        .font(.title3.weight(.black))
                        .foregroundStyle(.white)
                }
                Spacer()
                Image(systemName: "checkmark.shield.fill")
                    .font(.title2)
                    .foregroundStyle(.white)
            }
            HStack(spacing: 8) {
                overviewMetric("Priority", batch?.priority.count ?? 0)
                overviewMetric("Backups", batch?.backup.count ?? 0)
                overviewMetric("Reviewed", batch?.reviewedCount ?? 0)
            }
            VStack(alignment: .leading, spacing: 8) {
                Button {
                    Task { await state.enableRemotePush() }
                } label: {
                    Label("Enable real-time job alerts", systemImage: "bell.badge.fill")
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(.white)
                }
                Text(state.pushStatus)
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.80))
                HStack(spacing: 18) {
                    Button("Send test alert") { Task { await state.sendTestPush() } }
                    Button("Disable push") { Task { await state.disableRemotePush() } }
                }
                .font(.caption.weight(.semibold))
                .foregroundStyle(.white.opacity(0.90))
            }
            Button {
                Task {
                    do {
                        try await DailyReviewReminder.enable()
                        state.alertMessage = "A daily 9:15 AM IST review reminder is enabled. Real-time batch-ready push alerts still require Apple push configuration."
                    } catch {
                        state.alertMessage = error.localizedDescription
                    }
                }
            } label: {
                Label("Enable 9:15 AM reminder", systemImage: "bell.badge")
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(.white)
            }
        }
        .padding(18)
        .background(
            LinearGradient(colors: [HDTheme.navy, HDTheme.blue],
                           startPoint: .topLeading, endPoint: .bottomTrailing)
        )
        .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
    }

    private func overviewMetric(_ label: String, _ value: Int) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(String(value)).font(.title3.bold()).foregroundStyle(.white)
            Text(label).font(.caption2).foregroundStyle(.white.opacity(0.76))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(9)
        .background(.white.opacity(0.12))
        .clipShape(RoundedRectangle(cornerRadius: 10))
    }
}

struct DailyReviewCandidateCard: View {
    let candidate: ReviewCandidate
    let isPriority: Bool
    let backups: [ReviewCandidate]
    let isDisabled: Bool
    let onDecision: (String) -> Void
    let onReplace: (ReviewCandidate) -> Void

    private var compatibleBackups: [ReviewCandidate] {
        let wanted = bucket(candidate)
        return backups.filter { $0.reviewedStatus == "live" && bucket($0) == wanted }
    }

    private func bucket(_ item: ReviewCandidate) -> String {
        if item.categoryLabel == "Non-IT" { return "nonit" }
        if item.categoryLabel == "Internship" || item.categoryLabel == "Apprenticeship" { return "training" }
        return "it"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top, spacing: 12) {
                ZStack {
                    RoundedRectangle(cornerRadius: 11)
                        .fill(HDTheme.blue.opacity(0.10))
                    Text(String(candidate.company.prefix(2)).uppercased())
                        .font(.subheadline.weight(.black))
                        .foregroundStyle(HDTheme.blue)
                }
                .frame(width: 44, height: 44)

                VStack(alignment: .leading, spacing: 5) {
                    Text(candidate.company)
                        .font(.subheadline.weight(.bold))
                        .foregroundStyle(HDTheme.navy)
                    Text(candidate.role)
                        .font(.headline)
                        .fixedSize(horizontal: false, vertical: true)
                    Text([candidate.loc ?? candidate.job?.loc ?? "", candidate.expYears ?? candidate.job?.expYears ?? ""]
                            .filter { !$0.isEmpty }.joined(separator: " · "))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 0)
            }

            HStack(spacing: 8) {
                StatusPill(text: candidate.categoryLabel, color: HDTheme.blue)
                if candidate.reviewedStatus == "live" {
                    StatusPill(text: "Verified Live", color: HDTheme.green, icon: "checkmark.circle.fill")
                } else if candidate.reviewedStatus == "expired" {
                    StatusPill(text: "Expired", color: HDTheme.red, icon: "xmark.circle.fill")
                } else {
                    StatusPill(text: candidate.reviewedStatus == "unsure" ? "Unsure" : "Needs review",
                               color: HDTheme.amber)
                }
            }

            if let url = candidate.officialURL {
                Link(destination: url) {
                    Label("Open official application", systemImage: "arrow.up.right.square")
                        .font(.subheadline.weight(.semibold))
                }
            } else {
                Text("Official application link unavailable")
                    .font(.footnote)
                    .foregroundStyle(HDTheme.red)
            }

            HStack(spacing: 8) {
                decisionButton("Live", value: "live", icon: "checkmark.circle", color: HDTheme.green)
                decisionButton("Expired", value: "expired", icon: "xmark.circle", color: HDTheme.red)
                decisionButton("Unsure", value: "unsure", icon: "questionmark.circle", color: HDTheme.amber)
            }

            if isPriority {
                Menu {
                    if compatibleBackups.isEmpty {
                        Text("Verify a compatible backup as Live first")
                    } else {
                        ForEach(compatibleBackups) { item in
                            Button(item.company + " · " + item.role) { onReplace(item) }
                        }
                    }
                } label: {
                    Label("Replace from backup", systemImage: "arrow.left.arrow.right")
                        .font(.footnote.weight(.semibold))
                }
                .disabled(isDisabled || compatibleBackups.isEmpty)
            }

            if !candidate.isComplete {
                Text("Detailed job content not ready — publishing will remain disabled.")
                    .font(.caption)
                    .foregroundStyle(HDTheme.amber)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
        .premiumCard()
    }

    private func decisionButton(_ title: String, value: String, icon: String, color: Color) -> some View {
        Button { onDecision(value) } label: {
            VStack(spacing: 5) {
                Image(systemName: icon).font(.subheadline)
                Text(title).font(.caption2.weight(.semibold))
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 9)
            .foregroundStyle(candidate.reviewedStatus == value ? .white : color)
            .background(candidate.reviewedStatus == value ? color : color.opacity(0.09))
            .clipShape(RoundedRectangle(cornerRadius: 11))
        }
        .buttonStyle(.plain)
        .disabled(isDisabled)
    }
}
