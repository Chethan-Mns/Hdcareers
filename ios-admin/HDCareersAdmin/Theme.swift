import SwiftUI

enum HDTheme {
    static let blue = Color(red: 0.035, green: 0.412, blue: 0.855)
    static let navy = Color(red: 0.027, green: 0.102, blue: 0.200)
    static let background = Color(red: 0.965, green: 0.976, blue: 0.992)
    static let green = Color(red: 0.086, green: 0.639, blue: 0.290)
    static let amber = Color(red: 0.957, green: 0.620, blue: 0.035)
    static let red = Color(red: 0.862, green: 0.149, blue: 0.149)
}

struct HDCard: ViewModifier {
    var padding: CGFloat = 16

    func body(content: Content) -> some View {
        content
            .padding(padding)
            .background(.white)
            .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(Color.black.opacity(0.06), lineWidth: 1)
            }
            .shadow(color: .black.opacity(0.045), radius: 14, y: 6)
    }
}

extension View {
    func hdCard(_ padding: CGFloat = 16) -> some View {
        modifier(HDCard(padding: padding))
    }
}

struct HDLogoView: View {
    var size: CGFloat = 48

    var body: some View {
        Image("HDLogo")
            .resizable()
            .scaledToFit()
            .frame(width: size, height: size)
            .background(.white)
            .clipShape(RoundedRectangle(cornerRadius: size * 0.22, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: size * 0.22, style: .continuous)
                    .stroke(Color.black.opacity(0.06))
            }
    }
}

struct StatusPill: View {
    let text: String
    let color: Color
    var icon: String? = nil

    var body: some View {
        HStack(spacing: 5) {
            if let icon {
                Image(systemName: icon)
            }
            Text(text)
        }
        .font(.caption2.weight(.bold))
        .foregroundStyle(color)
        .padding(.horizontal, 9)
        .padding(.vertical, 6)
        .background(color.opacity(0.10))
        .clipShape(Capsule())
    }
}

struct EmptyState: View {
    let icon: String
    let title: String
    let message: String

    var body: some View {
        VStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 28, weight: .semibold))
                .foregroundStyle(.secondary)
            Text(title)
                .font(.headline)
            Text(message)
                .font(.subheadline)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 34)
    }
}


extension Color {
    init?(hex: String) {
        var value = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        if value.hasPrefix("#") { value.removeFirst() }
        guard value.count == 6, let rgb = Int(value, radix: 16) else { return nil }
        self.init(
            red: Double((rgb >> 16) & 0xFF) / 255.0,
            green: Double((rgb >> 8) & 0xFF) / 255.0,
            blue: Double(rgb & 0xFF) / 255.0
        )
    }
}

struct CompanyLogoView: View {
    let job: Job
    var size: CGFloat = 46

    private let localLogos: [String: String] = [
        "Infosys": "infosys.svg",
        "Zoho": "zoho.svg",
        "TCS": "tcs.svg",
        "Amazon": "amazon.svg",
        "Wipro": "wipro.svg",
        "Cognizant": "cognizant.svg",
        "Swiggy": "swiggy.svg",
        "HCLTech": "hcltech.svg",
        "Deloitte": "deloitte.svg",
        "ISRO": "isro.svg"
    ]

    private let companyDomains: [String: String] = [
        "Amazon.jobs": "amazon.com",
        "Amazon": "amazon.com",
        "IBM": "ibm.com",
        "PwC": "pwc.com",
        "PWC": "pwc.com",
        "Accenture": "accenture.com",
        "Infosys": "infosys.com",
        "Zoho": "zoho.com",
        "TCS": "tcs.com",
        "Wipro": "wipro.com",
        "Cognizant": "cognizant.com",
        "HCLTech": "hcltech.com",
        "Deloitte": "deloitte.com",
        "ISRO": "isro.gov.in",
        "Cohere Health": "coherehealth.com",
        "Hevo Data": "hevodata.com",
        "Qualcomm": "qualcomm.com",
        "SAP": "sap.com",
        "Priceline": "priceline.com",
        "Canonical": "canonical.com",
        "IndiGo": "goindigo.in"
    ]

    private var mark: String {
        if let logo = job.logo, let first = logo.first, !first.isEmpty {
            return first
        }
        let parts = (job.company ?? "HD").split(separator: " ")
        if parts.count >= 2 {
            return (String(parts[0].prefix(1)) + String(parts[1].prefix(1))).uppercased()
        }
        return String((job.company ?? "HD").prefix(2)).uppercased()
    }

    private var brandColor: Color {
        if let logo = job.logo, logo.count > 1, let color = Color(hex: logo[1]) {
            return color
        }
        return HDTheme.blue
    }

    private var remoteURL: URL? {
        if let raw = job.logoUrl?.trimmingCharacters(in: .whitespacesAndNewlines),
           !raw.isEmpty,
           let url = URL(string: raw) {
            return url
        }

        if let company = job.company, let file = localLogos[company] {
            return URL(string: "https://hdcareers.in/assets/logos/\(file)")
        }

        let company = job.company ?? ""
        var domain = companyDomains[company] ?? job.domain ?? ""
        domain = domain
            .replacingOccurrences(of: "https://", with: "")
            .replacingOccurrences(of: "http://", with: "")
            .split(separator: "/")
            .first
            .map(String.init) ?? ""

        guard !domain.isEmpty else { return nil }
        let encoded = ("https://" + domain).addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? domain
        return URL(string: "https://www.google.com/s2/favicons?domain_url=\(encoded)&sz=128")
    }

    var body: some View {
        Group {
            if let url = remoteURL {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .scaledToFit()
                            .padding(5)
                    default:
                        fallback
                    }
                }
            } else {
                fallback
            }
        }
        .frame(width: size, height: size)
        .background(.white)
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(Color.black.opacity(0.06))
        }
    }

    private var fallback: some View {
        ZStack {
            brandColor.opacity(0.12)
            Text(mark)
                .font(.system(size: mark.count > 4 ? 9 : 12, weight: .black, design: .rounded))
                .foregroundStyle(brandColor)
                .minimumScaleFactor(0.6)
                .lineLimit(1)
                .padding(.horizontal, 4)
        }
    }
}
