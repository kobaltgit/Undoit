import 'package:flutter/material.dart';
import '../theme.dart';

class SupportedFormats extends StatelessWidget {
  const SupportedFormats({super.key});

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.sizeOf(context).width;
    final isDesktop = screenWidth > 860;

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: 24,
        vertical: isDesktop ? 60 : 30,
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1100),
          child: Column(
            children: [
              const Text(
                'Поддерживает любые ваши файлы',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                  letterSpacing: -0.8,
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Undoit сохраняет историю любых расширений, а для ключевых форматов предлагает интеллектуальный просмотр.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 15, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 36),
              Wrap(
                spacing: 16,
                runSpacing: 16,
                alignment: WrapAlignment.center,
                children: const [
                  _FormatPill(
                    icon: Icons.picture_as_pdf_rounded,
                    title: 'PDF Документы',
                    exts: '.pdf',
                    badge: 'Visual Diff',
                    badgeColor: AppColors.primary,
                  ),
                  _FormatPill(
                    icon: Icons.brush_rounded,
                    title: 'Adobe Illustrator',
                    exts: '.ai',
                    badge: 'XMP Preview',
                    badgeColor: AppColors.secondary,
                  ),
                  _FormatPill(
                    icon: Icons.article_rounded,
                    title: 'Microsoft Word',
                    exts: '.docx',
                    badge: 'Text Extractor',
                    badgeColor: AppColors.accentGreen,
                  ),
                  _FormatPill(
                    icon: Icons.code_rounded,
                    title: 'Исходный код',
                    exts: '.rs, .py, .ts, .js, .json, .md',
                    badge: 'Line Diff',
                    badgeColor: AppColors.accentAmber,
                  ),
                  _FormatPill(
                    icon: Icons.image_rounded,
                    title: 'Растровая графика',
                    exts: '.png, .jpg, .svg, .webp',
                    badge: 'Visual Compare',
                    badgeColor: AppColors.primary,
                  ),
                  _FormatPill(
                    icon: Icons.folder_zip_rounded,
                    title: 'Любые бинарники',
                    exts: 'Архивы, базы, 3D модели',
                    badge: 'Zstd Snapshot',
                    badgeColor: AppColors.textMuted,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FormatPill extends StatelessWidget {
  final IconData icon;
  final String title;
  final String exts;
  final String badge;
  final Color badgeColor;

  const _FormatPill({
    required this.icon,
    required this.title,
    required this.exts,
    required this.badge,
    required this.badgeColor,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 320,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: badgeColor.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: badgeColor, size: 24),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        title,
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 14,
                          color: AppColors.textPrimary,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: badgeColor.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        badge,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: badgeColor,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  exts,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
