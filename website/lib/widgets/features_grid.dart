import 'package:flutter/material.dart';
import '../theme.dart';

class FeaturesGrid extends StatelessWidget {
  const FeaturesGrid({super.key});

  static const List<_FeatureItemData> _features = [
    _FeatureItemData(
      icon: Icons.visibility_rounded,
      iconColor: AppColors.primary,
      title: 'Визуальный дифф PDF и .AI',
      description:
          'Сравнивайте макеты Illustrator и многостраничные PDF в реальном времени. Интерактивный ползунок наглядно показывает мельчайшие сдвиги слоев и текста.',
    ),
    _FeatureItemData(
      icon: Icons.description_rounded,
      iconColor: AppColors.secondary,
      title: 'Полноценная поддержка DOCX',
      description:
          'Автоматически распаковывает файлы Microsoft Word, извлекает чистый текст и подсвечивает добавленные и удаленные фрагменты построчно.',
    ),
    _FeatureItemData(
      icon: Icons.lock_outline_rounded,
      iconColor: AppColors.accentGreen,
      title: '100% Офлайн & Приватность',
      description:
          'Ноль обращений в облако, никаких подписок или регистрации. Ваши конфиденциальные файлы, коммерческие договоры и код остаются строго на вашем диске.',
    ),
    _FeatureItemData(
      icon: Icons.speed_rounded,
      iconColor: AppColors.accentAmber,
      title: 'Zstandard + Хеши BLAKE3',
      description:
          'Высокоскоростное сжатие Zstd уменьшает объем хранилища в разы, а криптографический хеш BLAKE3 исключает дублирование идентичных копий.',
    ),
    _FeatureItemData(
      icon: Icons.open_in_new_rounded,
      iconColor: AppColors.primary,
      title: 'Открытие в один клик',
      description:
          'Кнопка «В приложении» открывает выбранную историческую версию в вашем обычном софте (Word, Photoshop, Acrobat) без риска повредить текущий файл.',
    ),
    _FeatureItemData(
      icon: Icons.mouse_rounded,
      iconColor: AppColors.secondary,
      title: 'Контекстное меню Windows',
      description:
          'Щелкните правой кнопкой мыши по любому файлу в Проводнике Windows и выберите «История версий Undoit» для мгновенного доступа к таймлайну.',
    ),
    _FeatureItemData(
      icon: Icons.memory_rounded,
      iconColor: AppColors.accentGreen,
      title: '< 25 МБ оперативной памяти',
      description:
          'Ядро на Rust и легковесный движок Tauri v2 потребляют в 8 раз меньше RAM, чем аналоги на Electron, тихо работая в системном трее.',
    ),
    _FeatureItemData(
      icon: Icons.restore_rounded,
      iconColor: AppColors.accentRose,
      title: 'Восстановление без потерь',
      description:
          'Откатите файл к любому моменту или экспортируйте снимок как отдельную копию. Программа всегда делает страховочный бекап перед перезаписью.',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.sizeOf(context).width;
    final isDesktop = screenWidth > 900;
    final isTablet = screenWidth > 600 && screenWidth <= 900;

    int crossAxisCount = 1;
    if (isDesktop) {
      crossAxisCount = 4;
    } else if (isTablet) {
      crossAxisCount = 2;
    }

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: 24,
        vertical: isDesktop ? 70 : 40,
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1200),
          child: Column(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.secondary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppColors.secondary.withValues(alpha: 0.3)),
                ),
                child: const Text(
                  'ВОЗМОЖНОСТИ',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppColors.secondary,
                    letterSpacing: 1.0,
                  ),
                ),
              ),
              const SizedBox(height: 14),
              const Text(
                'Всё необходимое для защиты от ошибок',
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
                'Создано для дизайнеров, инженеров, юристов и разработчиков, ценящих стабильность и скорость.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 15,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 40),

              // Grid of Cards
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _features.length,
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: crossAxisCount,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                  childAspectRatio: isDesktop ? 1.05 : 1.25,
                ),
                itemBuilder: (context, index) {
                  final item = _features[index];
                  return _FeatureCard(item: item);
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FeatureItemData {
  final IconData icon;
  final Color iconColor;
  final String title;
  final String description;

  const _FeatureItemData({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.description,
  });
}

class _FeatureCard extends StatefulWidget {
  final _FeatureItemData item;
  const _FeatureCard({required this.item});

  @override
  State<_FeatureCard> createState() => _FeatureCardState();
}

class _FeatureCardState extends State<_FeatureCard> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          color: _isHovered ? AppColors.surface : AppColors.card,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: _isHovered
                ? widget.item.iconColor.withValues(alpha: 0.5)
                : AppColors.surfaceBorder,
            width: 1.2,
          ),
          boxShadow: _isHovered
              ? [
                  BoxShadow(
                    color: widget.item.iconColor.withValues(alpha: 0.12),
                    blurRadius: 18,
                    offset: const Offset(0, 6),
                  ),
                ]
              : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: widget.item.iconColor.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(widget.item.icon, color: widget.item.iconColor, size: 24),
            ),
            const SizedBox(height: 16),
            Text(
              widget.item.title,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: Text(
                widget.item.description,
                style: const TextStyle(
                  fontSize: 13,
                  height: 1.5,
                  color: AppColors.textSecondary,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
