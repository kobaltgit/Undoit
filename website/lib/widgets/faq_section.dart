import 'package:flutter/material.dart';
import '../theme.dart';

class FaqSection extends StatelessWidget {
  const FaqSection({super.key});

  static const List<_FaqItemData> _items = [
    _FaqItemData(
      question: 'Как Undoit отслеживает файлы?',
      answer:
          'Приложение использует системный перехват событий файловой системы Windows на базе легковесного движка на Rust. В момент, когда вы нажимаете Ctrl+S в любой программе (Word, VS Code, Illustrator), Undoit фиксирует изменение, проверяет хеш BLAKE3 и сжимает снимок в локальную базу данных.',
    ),
    _FaqItemData(
      question: 'Где хранятся мои данные и есть ли облачная синхронизация?',
      answer:
          'Все данные хранятся исключительно на вашем жестком диске в локальной базе данных SQLite. Undoit на 100% автономен, работает без подключения к интернету и принципиально не отправляет ваши конфиденциальные документы ни на какие сторонние серверы.',
    ),
    _FaqItemData(
      question: 'Не заполнит ли история версий весь свободный диск?',
      answer:
          'Нет. Во-первых, файлы сжимаются эффективным алгоритмом Zstandard (Zstd). Во-вторых, встроенный механизм дедупликации хешей BLAKE3 гарантирует, что если файл не изменился по содержимому, новая копия на диск не запишется. Также в настройках можно задать автоочистку версий старше N дней.',
    ),
    _FaqItemData(
      question: 'Чем отличаются установщик (.exe setup) и портабельная версия?',
      answer:
          'Установщик автоматически прописывает приложение в автозагрузку Windows, создает ярлыки в меню «Пуск» и регистрирует пункт «История версий Undoit» в контекстном меню Проводника. Портабельная версия запускается в один клик без инсталляции и прав администратора — идеально для запуска с флешки.',
    ),
    _FaqItemData(
      question: 'Что произойдет, если я закрою окно программы?',
      answer:
          'При закрытии окна Undoit не прекращает работу, а бесшумно сворачивается в системный трей возле часов, продолжая защищать ваши документы. Из меню трея можно в один клик временно приостановить отслеживание или снова развернуть окно истории.',
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
          constraints: const BoxConstraints(maxWidth: 860),
          child: Column(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
                ),
                child: const Text(
                  'ВОПРОСЫ И ОТВЕТЫ',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: AppColors.primary,
                    letterSpacing: 1.0,
                  ),
                ),
              ),
              const SizedBox(height: 14),
              const Text(
                'Часто задаваемые вопросы',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.w800,
                  color: AppColors.textPrimary,
                  letterSpacing: -0.8,
                ),
              ),
              const SizedBox(height: 36),

              // FAQ Accordion List
              ListView.separated(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _items.length,
                separatorBuilder: (context, index) => const SizedBox(height: 12),
                itemBuilder: (context, index) {
                  final item = _items[index];
                  return Material(
                    color: AppColors.surface,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                      side: const BorderSide(color: AppColors.surfaceBorder),
                    ),
                    clipBehavior: Clip.antiAlias,
                    child: Theme(
                      data: Theme.of(context).copyWith(
                        dividerColor: Colors.transparent,
                      ),
                      child: ExpansionTile(
                        iconColor: AppColors.primary,
                        collapsedIconColor: AppColors.textSecondary,
                        title: Text(
                          item.question,
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        children: [
                          Padding(
                            padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                            child: Text(
                              item.answer,
                              style: const TextStyle(
                                fontSize: 14,
                                height: 1.6,
                                color: AppColors.textSecondary,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FaqItemData {
  final String question;
  final String answer;

  const _FaqItemData({required this.question, required this.answer});
}
