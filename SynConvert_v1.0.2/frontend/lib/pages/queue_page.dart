import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../backend_bridge.dart';

class QueuePage extends StatefulWidget {
  const QueuePage({super.key});

  @override
  State<QueuePage> createState() => _QueuePageState();
}

class _QueuePageState extends State<QueuePage> with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  List<Map<String, dynamic>>? _jobs;
  bool _isLoading = true;
  bool _isProcessing = false;
  final List<String> _consoleLog = [];
  final ScrollController _consoleScrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _refreshQueue();
  }

  Future<void> _refreshQueue() async {
    setState(() => _isLoading = true);
    try {
      final bridge = context.read<BackendBridge>();
      final jobs = await bridge.getQueueStatus();
      setState(() {
        _jobs = jobs;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _clearCompleted() async {
    try {
      await context.read<BackendBridge>().clearCompletedJobs();
      _refreshQueue();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: Colors.redAccent),
        );
      }
    }
  }

  Future<void> _resetFailed() async {
    try {
      await context.read<BackendBridge>().resetFailedJobs();
      _refreshQueue();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: Colors.redAccent),
        );
      }
    }
  }

  void _resumeQueue() {
    setState(() {
      _isProcessing = true;
      _consoleLog.clear();
      _consoleLog.add("🚀 Resuming conversion queue...");
    });

    final bridge = context.read<BackendBridge>();
    bridge.resumeQueue().listen(
      (line) {
        setState(() {
          // Smart log replacement for timer lines (the fix from v1.0.2)
          if (line.contains('⏱') && _consoleLog.isNotEmpty && _consoleLog.last.contains('⏱')) {
            _consoleLog[_consoleLog.length - 1] = line;
          } else {
            _consoleLog.add(line);
          }
        });
        
        // Auto-scroll
        if (_consoleScrollController.hasClients) {
          _consoleScrollController.animateTo(
            _consoleScrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeOut,
          );
        }
      },
      onDone: () {
        setState(() => _isProcessing = false);
        _refreshQueue();
      },
      onError: (e) {
        setState(() {
          _consoleLog.add("❌ Error: $e");
          _isProcessing = false;
        });
        _refreshQueue();
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Conversion Queue',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                  ),
                  Text(
                    'Manage your background tasks and pending jobs.',
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 14),
                  ),
                ],
              ),
              Row(
                children: [
                  _buildActionButton(
                    icon: Icons.play_arrow_rounded,
                    label: 'Resume Queue',
                    color: const Color(0xFF00D2FF),
                    onPressed: _jobs != null && _jobs!.any((j) => j['status'] == 'pending')
                        ? _resumeQueue
                        : null,
                  ),
                  const SizedBox(width: 12),
                  _buildActionButton(
                    icon: Icons.restore_rounded,
                    label: 'Reset Failed',
                    color: Colors.orangeAccent,
                    onPressed: _jobs != null && _jobs!.any((j) => j['status'] == 'failed')
                        ? _resetFailed
                        : null,
                  ),
                  const SizedBox(width: 12),
                  _buildActionButton(
                    icon: Icons.cleaning_services_rounded,
                    label: 'Clear Done',
                    color: Colors.white24,
                    onPressed: _jobs != null && _jobs!.any((j) => j['status'] == 'done' || j['status'] == 'skipped')
                        ? _clearCompleted
                        : null,
                  ),
                  const SizedBox(width: 12),
                  IconButton(
                    onPressed: _refreshQueue,
                    icon: const Icon(Icons.refresh_rounded, color: Colors.white70),
                    tooltip: 'Refresh Status',
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 32),
          if (_isLoading)
            const Expanded(child: Center(child: CircularProgressIndicator()))
          else if (_jobs == null || _jobs!.isEmpty)
            Expanded(
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.inbox_rounded, size: 64, color: Colors.white.withValues(alpha: 0.1)),
                    const SizedBox(height: 16),
                    Text(
                      'No jobs in queue',
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.3), fontSize: 18),
                    ),
                  ],
                ),
              ),
            )
          else
            Expanded(
              child: Container(
                decoration: BoxDecoration(
                  color: const Color(0xFF161616),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(24),
                  child: SingleChildScrollView(
                    child: DataTable(
                      headingRowColor: WidgetStateProperty.all(const Color(0xFF222222)),
                      columns: const [
                        DataColumn(label: Text('Status')),
                        DataColumn(label: Text('Source File')),
                        DataColumn(label: Text('Attempts')),
                        DataColumn(label: Text('Output')),
                      ],
                      rows: _jobs!.map((job) {
                        final status = job['status'] as String;
                        final source = job['source'] as String;
                        final filename = source.split('\\').last.split('/').last;
                        
                        Color statusColor = Colors.white70;
                        IconData statusIcon = Icons.help_outline;

                        switch (status) {
                          case 'pending':
                            statusColor = Colors.blueAccent;
                            statusIcon = Icons.hourglass_empty_rounded;
                            break;
                          case 'in_progress':
                            statusColor = Colors.orangeAccent;
                            statusIcon = Icons.sync_rounded;
                            break;
                          case 'done':
                            statusColor = const Color(0xFF2ECC71);
                            statusIcon = Icons.check_circle_rounded;
                            break;
                          case 'failed':
                            statusColor = Colors.redAccent;
                            statusIcon = Icons.error_rounded;
                            break;
                        }

                        return DataRow(
                          cells: [
                            DataCell(
                              Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(statusIcon, color: statusColor, size: 16),
                                  const SizedBox(width: 8),
                                  Text(
                                    status.toUpperCase(),
                                    style: TextStyle(
                                      color: statusColor,
                                      fontWeight: FontWeight.bold,
                                      fontSize: 10,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            DataCell(Text(filename, style: const TextStyle(fontSize: 12))),
                            DataCell(Text(job['attempts'].toString())),
                            DataCell(
                              Text(
                                job['output'].toString(),
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.4),
                                  fontSize: 10,
                                ),
                                overflow: TextOverflow.ellipsis,
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
          if (_isProcessing) _buildConsoleOverlay(),
        ],
      ),
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback? onPressed,
  }) {
    return ElevatedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon, size: 18),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: color.withValues(alpha: 0.1),
        foregroundColor: color,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: color.withValues(alpha: 0.2)),
        ),
      ),
    );
  }

  Widget _buildConsoleOverlay() {
    return Container(
      margin: const EdgeInsets.only(top: 24),
      height: 250,
      width: double.infinity,
      decoration: BoxDecoration(
        color: Colors.black,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF00D2FF).withValues(alpha: 0.3)),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(Icons.terminal_rounded, color: Color(0xFF00D2FF), size: 16),
                  SizedBox(width: 8),
                  Text('Processing Queue...',
                      style: TextStyle(color: Color(0xFF00D2FF), fontWeight: FontWeight.bold)),
                ],
              ),
              const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF00D2FF)),
              ),
            ],
          ),
          const Divider(color: Colors.white12, height: 24),
          Expanded(
            child: ListView.builder(
              controller: _consoleScrollController,
              itemCount: _consoleLog.length,
              itemBuilder: (context, index) {
                final line = _consoleLog[index];
                return Padding(
                  padding: const EdgeInsets.only(bottom: 4.0),
                  child: Text(
                    line,
                    style: TextStyle(
                      color: line.startsWith('❌') ? Colors.redAccent : Colors.white70,
                      fontFamily: 'monospace',
                      fontSize: 12,
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
