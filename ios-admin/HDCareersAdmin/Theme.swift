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
