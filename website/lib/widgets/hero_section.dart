import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../constants.dart';
import '../theme.dart';

class HeroSection extends StatelessWidget {
  final VoidCallback? onDownloadTap;

  const HeroSection({super.key, this.onDownloadTap});

  Future<void> _launchUrl(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.sizeOf(context).width;
    final isDesktop = screenWidth > 860;

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: 24,
        vertical: isDesktop ? 80 : 40,
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1100),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // Release Badge
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(30),
                  border: Border.all(color: AppColors.surfaceBorderHover.withValues(alpha: 0.3)),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primary.withValues(alpha: 0.08),
                      blurRadius: 16,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: const BoxDecoration(
                        color: AppColors.accentGreen,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 8),
                    const Flexible(
                      child: Text(
                        'Undoit 2.0.0 Релиз доступен — Перезапуск на Rust & Tauri',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 28),

              // Hero Heading
              Text(
                'Локальная машина времени\nдля ваших файлов на Windows',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: isDesktop ? 52 : 32,
                  fontWeight: FontWeight.w900,
                  letterSpacing: -1.5,
                  height: 1.15,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 20),

              // Subheading
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 760),
                child: Text(
                  'Невидимо сохраняет историю каждого изменения в реальном времени. Возвращайтесь к любой секунде работы, сравнивайте текст документов Word, код и находите визуальные отличия в PDF и макетах Illustrator прямо на экране.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: isDesktop ? 18 : 15,
                    fontWeight: FontWeight.w400,
                    height: 1.6,
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
              const SizedBox(height: 36),

              // Action Buttons
              Wrap(
                spacing: 16,
                runSpacing: 14,
                alignment: WrapAlignment.center,
                children: [
                  ElevatedButton.icon(
                    onPressed: () => _launchUrl(AppConstants.setupDownloadUrl),
                    icon: const Icon(Icons.download_rounded, size: 20),
                    label: const Text('Скачать установщик (.exe, 3.8 МБ)'),
                    style: ElevatedButton.styleFrom(
                      foregroundColor: const Color(0xFF030712),
                      backgroundColor: AppColors.primary,
                      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 18),
                      elevation: 0,
                      textStyle: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                  OutlinedButton.icon(
                    onPressed: () => _launchUrl(AppConstants.portableDownloadUrl),
                    icon: const Icon(Icons.flash_on_rounded, size: 18, color: AppColors.secondary),
                    label: const Text('Портабельная версия (.exe)'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.textPrimary,
                      side: const BorderSide(color: AppColors.surfaceBorderHover),
                      padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 18),
                      backgroundColor: AppColors.surface,
                      textStyle: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                  OutlinedButton.icon(
                    onPressed: () => _launchUrl(AppConstants.repoUrl),
                    icon: const Icon(Icons.code_rounded, size: 18, color: AppColors.textSecondary),
                    label: const Text('Исходный код'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.textSecondary,
                      side: const BorderSide(color: AppColors.surfaceBorder),
                      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
                      backgroundColor: Colors.transparent,
                      textStyle: const TextStyle(fontSize: 15),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 48),

              // Metrics / Highlights Row
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
                decoration: BoxDecoration(
                  color: AppColors.surface.withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppColors.surfaceBorder),
                ),
                child: Wrap(
                  spacing: isDesktop ? 48 : 24,
                  runSpacing: 16,
                  alignment: WrapAlignment.center,
                  children: const [
                    _MetricItem(value: '< 25 МБ', label: 'ОЗУ в фоне'),
                    _MetricItem(value: '3.8 МБ', label: 'Размер инсталлятора'),
                    _MetricItem(value: '100% Offline', label: 'Данные только у вас'),
                    _MetricItem(value: 'Zstandard', label: 'Мгновенное сжатие'),
                    _MetricItem(value: 'Rust Core', label: 'Tauri v2 + SQLite'),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MetricItem extends StatelessWidget {
  final String value;
  final String label;

  const _MetricItem({required this.value, required this.label});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          value,
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w800,
            color: AppColors.primary,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            color: AppColors.textSecondary,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}
