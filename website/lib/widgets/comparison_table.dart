import 'package:flutter/material.dart';
import '../i18n.dart';
import '../theme.dart';

class ComparisonTable extends StatelessWidget {
  const ComparisonTable({super.key});

  List<_ComparisonRowData> get _rows => [
    _ComparisonRowData(
      metric: S.compRow1Metric,
      v1: S.compRow1V1,
      v2: S.compRow1V2,
      isHighlight: false,
    ),
    _ComparisonRowData(
      metric: S.compRow2Metric,
      v1: S.compRow2V1,
      v2: S.compRow2V2,
      isHighlight: true,
    ),
    _ComparisonRowData(
      metric: S.compRow3Metric,
      v1: S.compRow3V1,
      v2: S.compRow3V2,
      isHighlight: true,
    ),
    _ComparisonRowData(
      metric: S.compRow4Metric,
      v1: S.compRow4V1,
      v2: S.compRow4V2,
      isHighlight: false,
    ),
    _ComparisonRowData(
      metric: S.compRow5Metric,
      v1: S.compRow5V1,
      v2: S.compRow5V2,
      isHighlight: false,
    ),
    _ComparisonRowData(
      metric: S.compRow6Metric,
      v1: S.compRow6V1,
      v2: S.compRow6V2,
      isHighlight: true,
    ),
    _ComparisonRowData(
      metric: S.compRow7Metric,
      v1: S.compRow7V1,
      v2: S.compRow7V2,
      isHighlight: true,
    ),
    _ComparisonRowData(
      metric: S.compRow8Metric,
      v1: S.compRow8V1,
      v2: S.compRow8V2,
      isHighlight: false,
    ),
    _ComparisonRowData(
      metric: S.compRow9Metric,
      v1: S.compRow9V1,
      v2: S.compRow9V2,
      isHighlight: true,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.sizeOf(context).width;
    final isDesktop = screenWidth > 860;
    final rows = _rows;

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
                child: Text(
                  S.compBadge,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppColors.accentGreen,
                    letterSpacing: 1.0,
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Text(
                S.compTitle,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 34,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                  letterSpacing: -0.8,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                S.compSubtitle,
                textAlign: TextAlign.center,
                style: const TextStyle(
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
                        columns: [
                          DataColumn(
                            label: Text(
                              S.compMetric,
                              style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white70),
                            ),
                          ),
                          DataColumn(
                            label: Text(
                              S.compLegacy,
                              style: const TextStyle(fontWeight: FontWeight.bold, color: AppColors.textMuted),
                            ),
                          ),
                          DataColumn(
                            label: Text(
                              S.compCurrent,
                              style: const TextStyle(
                                fontWeight: FontWeight.bold,
                                color: AppColors.primary,
                              ),
                            ),
                          ),
                        ],
                        rows: rows.map((row) {
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
