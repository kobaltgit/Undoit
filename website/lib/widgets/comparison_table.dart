import 'package:flutter/material.dart';
import '../theme.dart';

class ComparisonTable extends StatelessWidget {
  const ComparisonTable({super.key});

  static const List<_ComparisonRowData> _rows = [
    _ComparisonRowData(
      metric: 'Технологический стек',
      v1: 'Python 3 + PySide6 (Qt)',
      v2: 'Rust + Tauri v2 + SvelteKit',
      isHighlight: false,
    ),
    _ComparisonRowData(
      metric: 'Потребление ОЗУ в фоне',
      v1: '~150 – 200 МБ',
      v2: '15 – 25 МБ (в 8 раз меньше)',
      isHighlight: true,
    ),
    _ComparisonRowData(
      metric: 'Размер установщика',
      v1: '~80 МБ',
      v2: '3.86 МБ (NSIS setup)',
      isHighlight: true,
    ),
    _ComparisonRowData(
      metric: 'Сжатие версий на диске',
      v1: 'Стандартный zip',
      v2: 'Zstandard (Zstd) максимальной скорости',
      isHighlight: false,
    ),
    _ComparisonRowData(
      metric: 'Дедупликация файлов',
      v1: 'Базовая проверка размера',
      v2: 'Криптографический хеш BLAKE3',
      isHighlight: false,
    ),
    _ComparisonRowData(
      metric: 'Визуальный дифф PDF и .AI',
      v1: '❌ Отсутствует',
      v2: '✅ Сплит-слайдер и предпросмотр страниц',
      isHighlight: true,
    ),
    _ComparisonRowData(
      metric: 'Сравнение документов DOCX',
      v1: '❌ Бинарный файл',
      v2: '✅ Извлечение текста и построчный дифф',
      isHighlight: true,
    ),
    _ComparisonRowData(
      metric: 'Открытие во внешнем софте',
      v1: '❌ Только восстановить',
      v2: '✅ Кнопка «В приложении» (Word, AI, etc.)',
      isHighlight: false,
    ),
    _ComparisonRowData(
      metric: 'Холодный старт приложения',
      v1: '3 – 5 секунд',
      v2: '< 400 миллисекунд',
      isHighlight: true,
    ),
  ];

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
          constraints: const BoxConstraints(maxWidth: 1000),
          child: Column(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.accentGreen.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppColors.accentGreen.withValues(alpha: 0.3)),
                ),
                child: const Text(
                  'ЭВОЛЮЦИЯ ПРОЕКТА',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppColors.accentGreen,
                    letterSpacing: 1.0,
                  ),
                ),
              ),
              const SizedBox(height: 14),
              const Text(
                'Undoit 1.0 vs Undoit 2.0',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 34,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                  letterSpacing: -0.8,
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Почему переход на Rust и Tauri сделал приложение эталоном эффективности для Windows.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 15,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 36),

              // Table Box
              Container(
                decoration: BoxDecoration(
                  color: AppColors.card,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppColors.surfaceBorder),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.3),
                      blurRadius: 20,
                      offset: const Offset(0, 8),
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(15),
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: ConstrainedBox(
                      constraints: BoxConstraints(minWidth: isDesktop ? 960 : 700),
                      child: DataTable(
                        headingRowColor: WidgetStateProperty.all(const Color(0xFF0D121F)),
                        columnSpacing: 24,
                        dataRowMinHeight: 52,
                        dataRowMaxHeight: 56,
                        columns: const [
                          DataColumn(
                            label: Text(
                              'Характеристика',
                              style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white70),
                            ),
                          ),
                          DataColumn(
                            label: Text(
                              'Undoit v1.0 (Python)',
                              style: TextStyle(fontWeight: FontWeight.bold, color: AppColors.textMuted),
                            ),
                          ),
                          DataColumn(
                            label: Text(
                              'Undoit v2.0 (Rust + Tauri)',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                color: AppColors.primary,
                              ),
                            ),
                          ),
                        ],
                        rows: _rows.map((row) {
                          return DataRow(
                            color: row.isHighlight
                                ? WidgetStateProperty.all(AppColors.primary.withValues(alpha: 0.04))
                                : null,
                            cells: [
                              DataCell(
                                Text(
                                  row.metric,
                                  style: TextStyle(
                                    fontWeight: row.isHighlight ? FontWeight.w600 : FontWeight.w500,
                                    color: AppColors.textPrimary,
                                    fontSize: 13,
                                  ),
                                ),
                              ),
                              DataCell(
                                Text(
                                  row.v1,
                                  style: const TextStyle(
                                    color: AppColors.textMuted,
                                    fontSize: 13,
                                  ),
                                ),
                              ),
                              DataCell(
                                Text(
                                  row.v2,
                                  style: TextStyle(
                                    fontWeight: FontWeight.w700,
                                    color: row.isHighlight
                                        ? AppColors.accentGreen
                                        : AppColors.textPrimary,
                                    fontSize: 13,
                                  ),
                                ),
                              ),
                            ],
                          );
                        }).toList(),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ComparisonRowData {
  final String metric;
  final String v1;
  final String v2;
  final bool isHighlight;

  const _ComparisonRowData({
    required this.metric,
    required this.v1,
    required this.v2,
    required this.isHighlight,
  });
}
