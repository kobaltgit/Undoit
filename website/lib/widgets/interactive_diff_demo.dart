import 'package:flutter/material.dart';
import '../i18n.dart';
import '../theme.dart';

class InteractiveDiffDemo extends StatefulWidget {
  const InteractiveDiffDemo({super.key});

  @override
  State<InteractiveDiffDemo> createState() => _InteractiveDiffDemoState();
}

class _InteractiveDiffDemoState extends State<InteractiveDiffDemo> {
  double _splitRatio = 0.52; // 0.0 to 1.0
  int _selectedDemoIndex = 0; // 0: PDF, 1: Illustrator, 2: Code

  List<String> get _demoTitles => [
    S.isRu ? '📄 Договор_окончательный.pdf' : '📄 Contract_Final.pdf',
    S.isRu ? '🎨 Брендбук_знак.ai' : '🎨 Brandbook_Sign.ai',
    '⚡ engine_core.rs',
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
          constraints: const BoxConstraints(maxWidth: 1050),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // Section Header
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
                ),
                child: Text(
                  S.diffBadge,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppColors.primary,
                    letterSpacing: 1.0,
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Text(
                S.diffTitle,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                  letterSpacing: -0.8,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                S.diffSubtitle,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 15,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 28),

              // File Tabs Selector
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(_demoTitles.length, (index) {
                    final isSelected = _selectedDemoIndex == index;
                    return Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 6),
                      child: ChoiceChip(
                        label: Text(_demoTitles[index]),
                        selected: isSelected,
                        onSelected: (val) {
                          if (val) setState(() => _selectedDemoIndex = index);
                        },
                        selectedColor: AppColors.primary.withValues(alpha: 0.2),
                        backgroundColor: AppColors.surface,
                        side: BorderSide(
                          color: isSelected
                              ? AppColors.primary
                              : AppColors.surfaceBorder,
                        ),
                        labelStyle: TextStyle(
                          color: isSelected ? AppColors.primary : AppColors.textSecondary,
                          fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                          fontSize: 13,
                        ),
                      ),
                    );
                  }),
                ),
              ),
              const SizedBox(height: 24),

              // Interactive Diff Window Frame
              Container(
                height: isDesktop ? 480 : 380,
                decoration: BoxDecoration(
                  color: AppColors.card,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppColors.surfaceBorder, width: 1.5),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.5),
                      blurRadius: 30,
                      offset: const Offset(0, 12),
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(15),
                  child: Column(
                    children: [
                      // Window Top Bar
                      Container(
                        height: 42,
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        color: const Color(0xFF0C101A),
                        child: Row(
                          children: [
                            const Row(
                              children: [
                                _MacDot(color: Color(0xFFEF4444)),
                                SizedBox(width: 6),
                                _MacDot(color: Color(0xFFF59E0B)),
                                SizedBox(width: 6),
                                _MacDot(color: Color(0xFF10B981)),
                              ],
                            ),
                            const Spacer(),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                              decoration: BoxDecoration(
                                color: AppColors.surface,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(color: AppColors.surfaceBorder),
                              ),
                              child: Row(
                                children: [
                                  const Icon(Icons.compare_arrows_rounded, size: 14, color: AppColors.primary),
                                  const SizedBox(width: 6),
                                  Text(
                                    '${S.isRu ? "Сплит:" : "Split:"} ${(_splitRatio * 100).toInt()}%',
                                    style: const TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.w600,
                                      color: AppColors.textPrimary,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const Spacer(),
                            const Text(
                              'Undoit v2.1',
                              style: TextStyle(
                                fontSize: 11,
                                color: AppColors.textMuted,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),

                      // Canvas / Diff Workspace
                      Expanded(
                        child: LayoutBuilder(
                          builder: (context, constraints) {
                            final width = constraints.maxWidth;
                            final height = constraints.maxHeight;
                            final splitX = width * _splitRatio;

                            return MouseRegion(
                              cursor: SystemMouseCursors.resizeColumn,
                              child: GestureDetector(
                                behavior: HitTestBehavior.opaque,
                                onTapDown: (details) {
                                  setState(() {
                                    _splitRatio = (details.localPosition.dx / width).clamp(0.01, 0.99);
                                  });
                                },
                                onHorizontalDragUpdate: (details) {
                                  setState(() {
                                    // 2.8x speed multiplier: allows moving from 0% to 100% with a short mouse swipe!
                                    final deltaRatio = (details.delta.dx * 2.8) / width;
                                    _splitRatio = (_splitRatio + deltaRatio).clamp(0.01, 0.99);
                                  });
                                },
                                child: Stack(
                                  children: [
                                    // Layer 1: "Current" or "New" Version (Underneath)
                                    Positioned.fill(
                                      child: _buildRightSideContent(),
                                    ),

                                    // Layer 2: "Old" Version (Clipped to left of split)
                                    Positioned(
                                      top: 0,
                                      left: 0,
                                      bottom: 0,
                                      width: splitX,
                                      child: ClipRect(
                                        child: OverflowBox(
                                          alignment: Alignment.topLeft,
                                          maxWidth: width,
                                          maxHeight: height,
                                          minWidth: width,
                                          minHeight: height,
                                          child: _buildLeftSideContent(),
                                        ),
                                      ),
                                    ),

                                    // Vertical Divider Line & Draggable Handle
                                    Positioned(
                                      top: 0,
                                      bottom: 0,
                                      left: splitX - 16,
                                      width: 32,
                                      child: Center(
                                        child: Stack(
                                          alignment: Alignment.center,
                                          children: [
                                            // Vertical Line
                                            Container(
                                              width: 3,
                                              height: double.infinity,
                                              decoration: BoxDecoration(
                                                color: AppColors.primary,
                                                boxShadow: [
                                                  BoxShadow(
                                                    color: AppColors.primary.withValues(alpha: 0.8),
                                                    blurRadius: 8,
                                                  ),
                                                ],
                                              ),
                                            ),
                                            // Handle Knob
                                            Container(
                                              width: 32,
                                              height: 32,
                                              decoration: BoxDecoration(
                                                color: AppColors.primary,
                                                shape: BoxShape.circle,
                                                border: Border.all(color: Colors.white, width: 2),
                                                boxShadow: const [
                                                  BoxShadow(
                                                    color: Colors.black45,
                                                    blurRadius: 6,
                                                  ),
                                                ],
                                              ),
                                              child: const Icon(
                                                Icons.unfold_more_rounded,
                                                color: Color(0xFF07090E),
                                                size: 18,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),

                                    // Floating Labels: "Старая версия" and "Новая версия"
                                    Positioned(
                                      top: 12,
                                      left: 12,
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: Colors.black.withValues(alpha: 0.7),
                                          borderRadius: BorderRadius.circular(6),
                                          border: Border.all(color: AppColors.surfaceBorder),
                                        ),
                                        child: Text(
                                          S.isRu ? '◄ Версия #1 (Вчера 17:40)' : '◄ Version #1 (Yesterday 17:40)',
                                          style: const TextStyle(
                                            color: AppColors.textSecondary,
                                            fontSize: 11,
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                      ),
                                    ),
                                    Positioned(
                                      top: 12,
                                      right: 12,
                                      child: Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: AppColors.primary.withValues(alpha: 0.2),
                                          borderRadius: BorderRadius.circular(6),
                                          border: Border.all(color: AppColors.primary.withValues(alpha: 0.5)),
                                        ),
                                        child: Text(
                                          S.isRu ? 'Версия #2 (Сегодня 11:20) ►' : 'Version #2 (Today 11:20) ►',
                                          style: const TextStyle(
                                            color: AppColors.primary,
                                            fontSize: 11,
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Precision Slider & Direct Jump Controls
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  TextButton.icon(
                    onPressed: () => setState(() => _splitRatio = 0.02),
                    icon: const Icon(Icons.arrow_back_rounded, size: 14),
                    label: Text(S.diffWas),
                    style: TextButton.styleFrom(
                      foregroundColor: AppColors.textSecondary,
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    ),
                  ),
                  const SizedBox(width: 8),
                  SizedBox(
                    width: isDesktop ? 300 : 160,
                    child: SliderTheme(
                      data: SliderTheme.of(context).copyWith(
                        trackHeight: 4,
                        thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 8),
                        activeTrackColor: AppColors.primary,
                        inactiveTrackColor: AppColors.surfaceBorder,
                        thumbColor: AppColors.primary,
                        overlayColor: AppColors.primary.withValues(alpha: 0.2),
                      ),
                      child: Slider(
                        value: _splitRatio,
                        min: 0.01,
                        max: 0.99,
                        onChanged: (val) => setState(() => _splitRatio = val),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  TextButton.icon(
                    onPressed: () => setState(() => _splitRatio = 0.98),
                    icon: const Icon(Icons.arrow_forward_rounded, size: 14),
                    label: Text(S.diffNow),
                    style: TextButton.styleFrom(
                      foregroundColor: AppColors.primary,
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  // Left Side (Old)
  Widget _buildLeftSideContent() {
    switch (_selectedDemoIndex) {
      case 0: // PDF Document
        return _buildDocContent(
          title: S.isRu ? 'ДОГОВОР ОКАЗАНИЯ УСЛУГ' : 'SERVICE AGREEMENT',
          status: S.isRu ? 'Черновик (v1.0)' : 'Draft (v1.0)',
          statusColor: AppColors.accentAmber,
          clauseText: S.isRu
              ? '1.2. Стоимость работ составляет 85 000 руб. Срок выполнения: 45 рабочих дней.\n1.3. Авансовый платёж: не предусмотрен.'
              : '1.2. Total project cost is \$8,500. Delivery timeline: 45 business days.\n1.3. Advance deposit: None.',
          stampOpacity: 0.0,
        );
      case 1: // Illustrator Design
        return _buildDesignContent(
          accentColor: const Color(0xFF6366F1),
          title: 'PROTOTYPE V1',
          showGrid: true,
          elementCount: 2,
        );
      default: // Code
        return _buildCodeContent(isOld: true);
    }
  }

  // Right Side (New)
  Widget _buildRightSideContent() {
    switch (_selectedDemoIndex) {
      case 0: // PDF Document
        return _buildDocContent(
          title: S.isRu ? 'ДОГОВОР ОКАЗАНИЯ УСЛУГ' : 'SERVICE AGREEMENT',
          status: S.isRu ? 'Утверждён (v2.0)' : 'Approved (v2.0)',
          statusColor: AppColors.accentGreen,
          clauseText: S.isRu
              ? '1.2. Стоимость работ составляет 120 000 руб. Срок выполнения: 20 рабочих дней.\n1.3. Авансовый платёж: 50% в течение 3 банковских дней.'
              : '1.2. Total project cost is \$12,000. Delivery timeline: 20 business days.\n1.3. Advance deposit: 50% due within 3 business days.',
          stampOpacity: 0.9,
        );
      case 1: // Illustrator Design
        return _buildDesignContent(
          accentColor: const Color(0xFF06B6D4),
          title: 'FINAL LOGO V2',
          showGrid: false,
          elementCount: 4,
        );
      default: // Code
        return _buildCodeContent(isOld: false);
    }
  }

  Widget _buildDocContent({
    required String title,
    required String status,
    required Color statusColor,
    required String clauseText,
    required double stampOpacity,
  }) {
    return Container(
      color: const Color(0xFF1E2433),
      padding: const EdgeInsets.all(32),
      child: Stack(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.5,
                      color: Colors.white,
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: statusColor),
                    ),
                    child: Text(
                      status,
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: statusColor,
                      ),
                    ),
                  ),
                ],
              ),
              const Divider(color: Colors.white24, height: 28),
              Text(
                S.isRu ? '1. ПРЕДМЕТ ДОГОВОРА' : '1. SCOPE OF WORK',
                style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white70, fontSize: 13),
              ),
              const SizedBox(height: 8),
              Text(
                clauseText,
                style: const TextStyle(color: Colors.white, fontSize: 13, height: 1.6),
              ),
              const SizedBox(height: 16),
              Text(
                S.isRu
                    ? '2. ОТВЕТСТВЕННОСТЬ СТОРОН\nЗа нарушение сроков исполнитель выплачивает неустойку в размере 0.1% от суммы договора за каждый день просрочки.'
                    : '2. TERMS & LIABILITY\nProvider shall pay a late penalty of 0.1% of contract value per business day of unjustified delay.',
                style: const TextStyle(color: Colors.white60, fontSize: 12, height: 1.5),
              ),
            ],
          ),
          if (stampOpacity > 0)
            Positioned(
              right: 20,
              bottom: 20,
              child: Opacity(
                opacity: stampOpacity,
                child: Transform.rotate(
                  angle: -0.2,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                    decoration: BoxDecoration(
                      border: Border.all(color: AppColors.accentGreen, width: 2.5),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      S.isRu ? 'СОГЛАСОВАНО\nUNDOIТ 2.1' : 'APPROVED\nUNDOIТ 2.1',
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: AppColors.accentGreen,
                        fontWeight: FontWeight.w900,
                        fontSize: 12,
                        letterSpacing: 1.0,
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildDesignContent({
    required Color accentColor,
    required String title,
    required bool showGrid,
    required int elementCount,
  }) {
    return Container(
      color: const Color(0xFF0F172A),
      child: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 110,
              height: 110,
              decoration: BoxDecoration(
                color: accentColor.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(elementCount > 2 ? 32 : 12),
                border: Border.all(color: accentColor, width: 3),
                boxShadow: [
                  BoxShadow(
                    color: accentColor.withValues(alpha: 0.4),
                    blurRadius: 24,
                  ),
                ],
              ),
              child: Icon(
                elementCount > 2 ? Icons.verified_rounded : Icons.crop_square_rounded,
                color: accentColor,
                size: 54,
              ),
            ),
            const SizedBox(height: 18),
            Text(
              title,
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: accentColor,
                letterSpacing: 2,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              showGrid
                  ? (S.isRu ? 'Векторные направляющие включены' : 'Vector guides enabled')
                  : (S.isRu ? 'Отрендерено с оптимизацией кривых' : 'Rendered with curve optimization'),
              style: const TextStyle(fontSize: 12, color: Colors.white54),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCodeContent({required bool isOld}) {
    return Container(
      color: const Color(0xFF0D1117),
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            '// src-tauri/src/storage.rs',
            style: TextStyle(color: Colors.white38, fontSize: 12, fontFamily: 'monospace'),
          ),
          const SizedBox(height: 12),
          Text(
            isOld
                ? (S.isRu
                    ? 'pub fn save_version(data: &[u8]) -> Result<String> {\n    // Старый медленный алгоритм\n    let hash = md5::compute(data);\n    let compressed = gzip::compress(data)?;\n    fs::write(path, compressed)?;\n    Ok(hash)\n}'
                    : 'pub fn save_version(data: &[u8]) -> Result<String> {\n    // Legacy slow algorithm\n    let hash = md5::compute(data);\n    let compressed = gzip::compress(data)?;\n    fs::write(path, compressed)?;\n    Ok(hash)\n}')
                : (S.isRu
                    ? 'pub fn save_version(data: &[u8]) -> Result<String> {\n    // Undoit 2.1: BLAKE3 + Zstandard\n    let hash = blake3::hash(data).to_hex();\n    let compressed = zstd::encode_all(data, 3)?;\n    db::insert_version(&hash, &compressed)?;\n    Ok(hash.to_string())\n}'
                    : 'pub fn save_version(data: &[u8]) -> Result<String> {\n    // Undoit 2.1: BLAKE3 + Zstandard\n    let hash = blake3::hash(data).to_hex();\n    let compressed = zstd::encode_all(data, 3)?;\n    db::insert_version(&hash, &compressed)?;\n    Ok(hash.to_string())\n}'),
            style: TextStyle(
              color: isOld ? const Color(0xFFF87171) : const Color(0xFF4ADE80),
              fontSize: 13,
              height: 1.6,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }
}

class _MacDot extends StatelessWidget {
  final Color color;
  const _MacDot({required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 10,
      height: 10,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
      ),
    );
  }
}
