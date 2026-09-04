import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../constants.dart';
import '../i18n.dart';
import '../theme.dart';

class NavBar extends StatelessWidget {
  final VoidCallback? onFeaturesTap;
  final VoidCallback? onDiffDemoTap;
  final VoidCallback? onComparisonTap;
  final VoidCallback? onFaqTap;
  final VoidCallback? onDownloadTap;

  const NavBar({
    super.key,
    this.onFeaturesTap,
    this.onDiffDemoTap,
    this.onComparisonTap,
    this.onFaqTap,
    this.onDownloadTap,
  });

  Future<void> _launchUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDesktop = MediaQuery.sizeOf(context).width > 860;

    return ValueListenableBuilder<AppLang>(
      valueListenable: currentLang,
      builder: (context, lang, _) {
        final isRu = lang == AppLang.ru;

        return Container(
          height: 72,
          padding: const EdgeInsets.symmetric(horizontal: 24),
          decoration: BoxDecoration(
            color: AppColors.background.withValues(alpha: 0.85),
            border: const Border(
              bottom: BorderSide(color: AppColors.surfaceBorder, width: 1),
            ),
          ),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1200),
              child: Row(
                children: [
                  // Logo & App Name
                  Row(
                    children: [
                      Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          gradient: AppColors.primaryGradient,
                          borderRadius: BorderRadius.circular(10),
                          boxShadow: const [
                            BoxShadow(
                              color: AppColors.primaryGlow,
                              blurRadius: 12,
                              offset: Offset(0, 2),
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.history_rounded,
                          color: Colors.white,
                          size: 22,
                        ),
                      ),
                      const SizedBox(width: 12),
                      const Text(
                        'Undoit',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w800,
                          letterSpacing: -0.5,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: AppColors.primary.withValues(alpha: 0.4),
                          ),
                        ),
                        child: const Text(
                          'v2.1',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: AppColors.primary,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const Spacer(),

                  // Desktop Menu Items
                  if (isDesktop) ...[
                    Flexible(
                      child: SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            _NavLink(title: S.navFeatures, onTap: onFeaturesTap),
                            _NavLink(title: S.navDiffDemo, onTap: onDiffDemoTap),
                            _NavLink(title: S.navComparison, onTap: onComparisonTap),
                            _NavLink(title: S.navFaq, onTap: onFaqTap),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                  ],

                  // Language Switcher (RU / EN)
                  Container(
                    decoration: BoxDecoration(
                      color: AppColors.surface,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: AppColors.surfaceBorder),
                    ),
                    padding: const EdgeInsets.all(3),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _LangButton(
                          label: 'RU',
                          isActive: isRu,
                          onTap: () => setAppLanguage(AppLang.ru),
                        ),
                        const SizedBox(width: 2),
                        _LangButton(
                          label: 'EN',
                          isActive: !isRu,
                          onTap: () => setAppLanguage(AppLang.en),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 12),

                  // GitHub Star Button
                  OutlinedButton.icon(
                    onPressed: () => _launchUrl(AppConstants.repoUrl),
                    icon: const Icon(Icons.star_rounded, size: 18, color: AppColors.accentAmber),
                    label: const Text('GitHub'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.textPrimary,
                      side: const BorderSide(color: AppColors.surfaceBorder),
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      backgroundColor: AppColors.surface,
                    ),
                  ),
                  const SizedBox(width: 12),

                  // Download CTA
                  ElevatedButton.icon(
                    onPressed: onDownloadTap,
                    icon: const Icon(Icons.download_rounded, size: 18),
                    label: Text(S.navDownload),
                    style: ElevatedButton.styleFrom(
                      foregroundColor: const Color(0xFF030712),
                      backgroundColor: AppColors.primary,
                      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                      elevation: 0,
                      textStyle: const TextStyle(fontWeight: FontWeight.w700),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _LangButton extends StatelessWidget {
  final String label;
  final bool isActive;
  final VoidCallback onTap;

  const _LangButton({
    required this.label,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
          decoration: BoxDecoration(
            color: isActive ? AppColors.primary : Colors.transparent,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w800,
              color: isActive ? const Color(0xFF030712) : AppColors.textSecondary,
            ),
          ),
        ),
      ),
    );
  }
}

class _NavLink extends StatelessWidget {
  final String title;
  final VoidCallback? onTap;

  const _NavLink({required this.title, this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: TextButton(
        onPressed: onTap,
        style: TextButton.styleFrom(
          foregroundColor: AppColors.textSecondary,
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          textStyle: const TextStyle(fontWeight: FontWeight.w500, fontSize: 14),
        ),
        child: Text(title),
      ),
    );
  }
}
