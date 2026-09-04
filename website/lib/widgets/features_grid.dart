import 'package:flutter/material.dart';
import '../i18n.dart';
import '../theme.dart';

class FeaturesGrid extends StatelessWidget {
  const FeaturesGrid({super.key});

  List<_FeatureItemData> get _features => [
    _FeatureItemData(
      icon: Icons.visibility_rounded,
      iconColor: AppColors.primary,
      title: S.feat1Title,
      description: S.feat1Desc,
    ),
    _FeatureItemData(
      icon: Icons.description_rounded,
      iconColor: AppColors.secondary,
      title: S.feat2Title,
      description: S.feat2Desc,
    ),
    _FeatureItemData(
      icon: Icons.lock_outline_rounded,
      iconColor: AppColors.accentGreen,
      title: S.feat3Title,
      description: S.feat3Desc,
    ),
    _FeatureItemData(
      icon: Icons.speed_rounded,
      iconColor: AppColors.accentAmber,
      title: S.feat4Title,
      description: S.feat4Desc,
    ),
    _FeatureItemData(
      icon: Icons.open_in_new_rounded,
      iconColor: AppColors.primary,
      title: S.feat5Title,
      description: S.feat5Desc,
    ),
    _FeatureItemData(
      icon: Icons.mouse_rounded,
      iconColor: AppColors.secondary,
      title: S.feat6Title,
      description: S.feat6Desc,
    ),
    _FeatureItemData(
      icon: Icons.memory_rounded,
      iconColor: AppColors.accentGreen,
      title: S.feat7Title,
      description: S.feat7Desc,
    ),
    _FeatureItemData(
      icon: Icons.restore_rounded,
      iconColor: AppColors.accentRose,
      title: S.feat8Title,
      description: S.feat8Desc,
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

    final features = _features;

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
                child: Text(
                  S.featuresBadge,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppColors.secondary,
                    letterSpacing: 1.0,
                  ),
                ),
              ),
              const SizedBox(height: 14),
              Text(
                S.featuresTitle,
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
                S.featuresSubtitle,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 15,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 40),

              // Grid of Cards
              GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: features.length,
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: crossAxisCount,
                  crossAxisSpacing: 16,
                  mainAxisSpacing: 16,
                  childAspectRatio: isDesktop ? 1.05 : 1.25,
                ),
                itemBuilder: (context, index) {
                  final item = features[index];
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
