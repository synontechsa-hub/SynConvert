import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'backend_bridge.dart';
import 'pages/dashboard_page.dart';
import 'pages/wizard_page.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        Provider(create: (_) => BackendBridge()),
      ],
      child: const SynConvertApp(),
    ),
  );
}

class SynConvertApp extends StatelessWidget {
  const SynConvertApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SynConvert',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF00D2FF),
          brightness: Brightness.dark,
          surface: const Color(0xFF0E0E0E),
          primary: const Color(0xFF00D2FF),
          secondary: const Color(0xFF7000FF),
        ),
        textTheme: GoogleFonts.interTextTheme(ThemeData.dark().textTheme),
        scaffoldBackgroundColor: const Color(0xFF0A0A0A),
        cardTheme: CardThemeData(
          color: const Color(0xFF161616),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          elevation: 0,
        ),
      ),
      home: const MainLayout(),
    );
  }
}

class MainLayout extends StatefulWidget {
  const MainLayout({super.key});

  @override
  State<MainLayout> createState() => _MainLayoutState();
}

class _MainLayoutState extends State<MainLayout> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          NavigationRail(
            selectedIndex: _selectedIndex,
            onDestinationSelected: (int index) {
              setState(() {
                _selectedIndex = index;
              });
            },
            labelType: NavigationRailLabelType.all,
            backgroundColor: const Color(0xFF0E0E0E),
            // FIX: withOpacity deprecated — use withValues(alpha:) instead
            indicatorColor: const Color(0xFF00D2FF).withValues(alpha: 0.2),
            selectedIconTheme: const IconThemeData(color: Color(0xFF00D2FF)),
            unselectedIconTheme: IconThemeData(
              color: Colors.white.withValues(alpha: 0.4),
            ),
            selectedLabelTextStyle: const TextStyle(
              color: Color(0xFF00D2FF),
              fontWeight: FontWeight.bold,
            ),
            unselectedLabelTextStyle: TextStyle(
              color: Colors.white.withValues(alpha: 0.4),
            ),
            leading: Column(
              children: [
                const SizedBox(height: 16),
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF00D2FF), Color(0xFF7000FF)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.bolt, color: Colors.white, size: 32),
                ),
                const SizedBox(height: 32),
              ],
            ),
            destinations: const [
              NavigationRailDestination(
                icon: Icon(Icons.dashboard_rounded),
                label: Text('Dashboard'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.add_to_photos_rounded),
                label: Text('New Job'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.queue_play_next_rounded),
                label: Text('Queue'),
              ),
              NavigationRailDestination(
                icon: Icon(Icons.settings_rounded),
                label: Text('Settings'),
              ),
            ],
          ),
          const VerticalDivider(thickness: 1, width: 1, color: Color(0xFF222222)),
          Expanded(
            child: _buildBody(),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    return IndexedStack(
      index: _selectedIndex,
      children: const [
        DashboardPage(),
        WizardPage(),
        // Placeholder for Queue
        Center(child: Text('Queue Coming Soon')),
        // Placeholder for Settings
        Center(child: Text('Settings Coming Soon')),
      ],
    );
  }
}
