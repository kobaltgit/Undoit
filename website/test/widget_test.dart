import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:website/main.dart';

void main() {
  testWidgets('UndoitWebsiteApp smoke test', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    await tester.pumpWidget(const UndoitWebsiteApp());
    expect(find.text('Undoit'), findsWidgets);
  });
}
