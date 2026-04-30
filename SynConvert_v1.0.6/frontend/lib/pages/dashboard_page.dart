import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../backend_bridge.dart';

class DashboardPage extends StatefulWidget {
  const DashboardPage({super.key});

  @override
  State<DashboardPage> createState() => _DashboardPageState();
}

class DashboardData {
  final BackendStatus status;
  final int activeJobs;
  final double processedGB;

  DashboardData(this.status, this.activeJobs, this.processedGB);
}

class _DashboardPageState extends State<DashboardPage> {
  late Future<DashboardData> _dataFuture;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  void _refresh() {
    setState(() {
      _dataFuture = _fetchData();
    });
  }

  Future<DashboardData> _fetchData() async {
    final bridge = context.read<BackendBridge>();
    final status = await bridge.checkStatus();
    
    int active = 0;
    double processed = 0.0;
    
    if (status == BackendStatus.ready) {
      final queueData = await bridge.getQueueStatus();
      if (queueData.containsKey('stats')) {
        final stats = queueData['stats'] as Map<String, dynamic>;
        active = (stats['active_jobs'] as num?)?.toInt() ?? 0;
        processed = (stats['processed_gb'] as num?)?.toDouble() ?? 0.0;
      }
    }
    
    return DashboardData(status, active, processed);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'System Overview',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: Theme.of(context).colorScheme.onSurface,
                        ),
                  ),
                  const SizedBox(height: 8),
                  // FIX: withOpacity deprecated — use withValues(alpha:)
                  Text(
                    'Monitor your conversion engine and hardware status.',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
                ],
              ),
              const Spacer(),
              IconButton(
                onPressed: _refresh,
                icon: const Icon(Icons.refresh_rounded),
                tooltip: 'Refresh status',
                color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.4),
              ),
            ],
          ),
          const SizedBox(height: 32),
          FutureBuilder<DashboardData>(
            future: _dataFuture,
            builder: (context, snapshot) {
              // Show loading state while checking
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Row(
                  children: [
                    Expanded(
                      child: SizedBox(
                        height: 120,
                        child: Center(child: CircularProgressIndicator()),
                      ),
                    ),
                  ],
                );
              }

              final data = snapshot.data ?? DashboardData(BackendStatus.error, 0, 0.0);
              final status = data.status;
              final isReady = status == BackendStatus.ready;

              return Row(
                children: [
                  _StatusCard(
                    title: 'Engine Status',
                    value: _statusToString(status),
                    icon: isReady
                        ? Icons.check_circle_rounded
                        : Icons.warning_rounded,
                    color: isReady
                        ? const Color(0xFF00D2FF)
                        : Colors.redAccent,
                  ),
                  const SizedBox(width: 24),
                  _StatusCard(
                    title: 'Active Jobs',
                    value: '${data.activeJobs}',
                    icon: Icons.alt_route_rounded,
                    color: const Color(0xFF7000FF),
                  ),
                  const SizedBox(width: 24),
                  _StatusCard(
                    title: 'Processed',
                    value: '${data.processedGB.toStringAsFixed(2)} GB',
                    icon: Icons.data_usage_rounded,
                    color: Colors.orangeAccent,
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  String _statusToString(BackendStatus status) {
    // FIX: exhaustive switch with no default needed since BackendStatus is
    // a sealed enum — but keeping return outside switch for safety
    switch (status) {
      case BackendStatus.ready:
        return 'Ready';
      case BackendStatus.pythonMissing:
        return 'Python Not Found';
      case BackendStatus.moduleMissing:
        return 'Module Error';
      case BackendStatus.error:
        return 'Disconnected';
    }
  }
}

class _StatusCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;

  const _StatusCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          borderRadius: BorderRadius.circular(24),
          // FIX: withOpacity deprecated — use withValues(alpha:)
          border: Border.all(color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.05)),
          boxShadow: [
            BoxShadow(
              color: color.withValues(alpha: 0.05),
              blurRadius: 20,
              offset: const Offset(0, 10),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Icon(icon, color: color, size: 28),
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: color,
                    shape: BoxShape.circle,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),
            Text(
              value,
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: Theme.of(context).colorScheme.onSurface,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              title,
              style: TextStyle(
                color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.4),
                fontSize: 14,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
