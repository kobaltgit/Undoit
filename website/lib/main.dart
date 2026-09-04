import 'package:flutter/material.dart';
import 'i18n.dart';
import 'theme.dart';
import 'widgets/navbar.dart';
import 'widgets/hero_section.dart';
import 'widgets/interactive_diff_demo.dart';
import 'widgets/features_grid.dart';
import 'widgets/comparison_table.dart';
import 'widgets/supported_formats.dart';
import 'widgets/faq_section.dart';
import 'widgets/download_cta.dart';
import 'widgets/footer.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const UndoitWebsiteApp());
}

class UndoitWebsiteApp extends StatelessWidget {
  const UndoitWebsiteApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<AppLang>(
      valueListenable: currentLang,
      builder: (context, lang, _) {
        return MaterialApp(
          key: ValueKey('app_$lang'),
          title: lang == AppLang.ru
              ? 'Undoit — Локальная машина времени для ваших файлов'
              : 'Undoit — Local Time Machine for Your Files',
          debugShowCheckedModeBanner: false,
          theme: buildAppTheme(),
          home: LandingPage(key: ValueKey('landing_$lang')),
        );
      },
    );
  }
}

class LandingPage extends StatefulWidget {
  const LandingPage({super.key});

  @override
  State<LandingPage> createState() => _LandingPageState();
}

class _LandingPageState extends State<LandingPage> {
  final ScrollController _scrollController = ScrollController();

  final GlobalKey _featuresKey = GlobalKey();
  final GlobalKey _diffDemoKey = GlobalKey();
  final GlobalKey _comparisonKey = GlobalKey();
  final GlobalKey _faqKey = GlobalKey();
  final GlobalKey _downloadKey = GlobalKey();

  void _scrollToKey(GlobalKey key) {
    final context = key.currentContext;
    if (context != null) {
      Scrollable.ensureVisible(
        context,
        duration: const Duration(milliseconds: 600),
        curve: Curves.easeInOutCubic,
      );
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: Stack(
        children: [
          // Background ambient gradient glow
          Positioned(
            top: -150,
            left: 0,
            right: 0,
            height: 600,
            child: Container(
              decoration: const BoxDecoration(
                gradient: AppColors.heroGlowGradient,
              ),
            ),
          ),

          // Main scrollable content
          Column(
            children: [
              // Sticky Navigation Bar
              NavBar(
                onFeaturesTap: () => _scrollToKey(_featuresKey),
                onDiffDemoTap: () => _scrollToKey(_diffDemoKey),
                onComparisonTap: () => _scrollToKey(_comparisonKey),
                onFaqTap: () => _scrollToKey(_faqKey),
                onDownloadTap: () => _scrollToKey(_downloadKey),
              ),

              // Page sections
              Expanded(
                child: SingleChildScrollView(
                  controller: _scrollController,
                  physics: const BouncingScrollPhysics(),
                  child: Column(
                    children: [
                      HeroSection(
                        onDownloadTap: () => _scrollToKey(_downloadKey),
                      ),
                      Container(
                        key: _diffDemoKey,
                        child: InteractiveDiffDemo(),
                      ),
                      Container(
                        key: _featuresKey,
                        child: FeaturesGrid(),
                      ),
                      Container(
                        key: _comparisonKey,
                        child: ComparisonTable(),
                      ),
                      SupportedFormats(),
                      Container(
                        key: _faqKey,
                        child: FaqSection(),
                      ),
                      Container(
                        key: _downloadKey,
                        child: DownloadCta(),
                      ),
                      AppFooter(),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
