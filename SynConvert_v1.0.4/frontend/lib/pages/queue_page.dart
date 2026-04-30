import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:desktop_drop/desktop_drop.dart';
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
  final Set<String> _selectedIds = {};
  bool _isDragging = false;


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

  Future<void> _removeSelected() async {
    if (_selectedIds.isEmpty) return;
    try {
      await context.read<BackendBridge>().removeJobs(_selectedIds.toList());
      _selectedIds.clear();
      _refreshQueue();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: Colors.redAccent),
        );
      }
    }
  }

  Future<void> _clearAllHistory() async {
    final bridge = context.read<BackendBridge>();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF161616),
        title: const Text('Clear All History', style: TextStyle(color: Colors.white)),
        content: const Text(
          'This will remove all completed, failed, and skipped jobs from the queue. Pending jobs will be kept. Continue?',
          style: TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.redAccent),
            child: const Text('Clear All'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await bridge.clearAllHistory();
        _refreshQueue();
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Error: $e'), backgroundColor: Colors.redAccent),
          );
        }
      }
    }
  }

  Future<void> _stopProcessing() async {
    await context.read<BackendBridge>().stopActiveProcess();
    setState(() {
      _isProcessing = false;
      _consoleLog.add("🛑 Processing stopped by user.");
    });
    _refreshQueue();
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
          // Parallel Smart Append: 
          // If the new line is a progress update (⏱), 
          // find the existing progress line for the SAME job ID and update it.
          if (line.contains('⏱')) {
            final jobIdMatch = RegExp(r'\[(.*?)\]').firstMatch(line);
            final jobId = jobIdMatch?.group(1);
            
            if (jobId != null) {
              final existingIndex = _consoleLog.indexWhere(
                (l) => l.contains('[$jobId]') && l.contains('⏱')
              );
              
              if (existingIndex != -1) {
                _consoleLog[existingIndex] = line;
              } else {
                _consoleLog.add(line);
              }
            } else {
              _consoleLog.add(line);
            }
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
    return DropTarget(
      onDragDone: (details) async {
        final bridge = context.read<BackendBridge>();
        final messenger = ScaffoldMessenger.of(context);
        final paths = details.files
            .map((f) => f.path)
            .where((p) => FileSystemEntity.isFileSync(p))
            .toList();
        if (paths.isNotEmpty) {
          try {
            await bridge.addToQueue(paths);
            _refreshQueue();
          } catch (e) {
            if (mounted) {
              messenger.showSnackBar(
                SnackBar(
                    content: Text('Error adding to queue: $e'),
                    backgroundColor: Colors.redAccent),
              );
            }
          }
        }
      },
      onDragEntered: (details) => setState(() => _isDragging = true),
      onDragExited: (details) => setState(() => _isDragging = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        decoration: BoxDecoration(
          color: _isDragging
              ? Colors.white.withValues(alpha: 0.05)
              : Colors.transparent,
        ),
        child: Padding(
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
                        style: Theme.of(context)
                            .textTheme
                            .headlineMedium
                            ?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                      ),
                      Text(
                        'Manage your background tasks and pending jobs.',
                        style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.4),
                            fontSize: 14),
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      if (_selectedIds.isNotEmpty)
                        _buildActionButton(
                          icon: Icons.delete_sweep_rounded,
                          label: 'Remove Selected (${_selectedIds.length})',
                          color: Colors.redAccent,
                          onPressed: _removeSelected,
                        )
                      else ...[
                        if (_isProcessing)
                          _buildActionButton(
                            icon: Icons.stop_rounded,
                            label: 'Stop Processing',
                            color: Colors.redAccent,
                            onPressed: _stopProcessing,
                          )
                        else
                          _buildActionButton(
                            icon: Icons.play_arrow_rounded,
                            label: 'Resume Queue',
                            color: const Color(0xFF00D2FF),
                            onPressed: _jobs != null &&
                                    _jobs!.any((j) => j['status'] == 'pending')
                                ? _resumeQueue
                                : null,
                          ),
                        const SizedBox(width: 12),
                        _buildActionButton(
                          icon: Icons.restore_rounded,
                          label: 'Reset Failed',
                          color: Colors.orangeAccent,
                          onPressed: _jobs != null &&
                                  _jobs!.any((j) => j['status'] == 'failed')
                              ? _resetFailed
                              : null,
                        ),
                      ],
                      const SizedBox(width: 12),
                      _buildActionButton(
                        icon: Icons.cleaning_services_rounded,
                        label: 'Clear Done',
                        color: Colors.white24,
                        onPressed: _jobs != null &&
                                _jobs!.any((j) =>
                                    j['status'] == 'done' ||
                                    j['status'] == 'skipped')
                            ? _clearCompleted
                            : null,
                      ),
                      const SizedBox(width: 12),
                      _buildActionButton(
                        icon: Icons.history_rounded,
                        label: 'Clear History',
                        color: Colors.redAccent.withValues(alpha: 0.5),
                        onPressed: _jobs != null &&
                                _jobs!.any((j) =>
                                    j['status'] != 'pending' &&
                                    j['status'] != 'in_progress')
                            ? _clearAllHistory
                            : null,
                      ),
                      const SizedBox(width: 12),
                      IconButton(
                        onPressed: _refreshQueue,
                        icon: const Icon(Icons.refresh_rounded,
                            color: Colors.white70),
                        tooltip: 'Refresh Status',
                      ),
                    ],
                  ),
                ],
              ),
              const SizedBox(height: 32),
              if (_isLoading)
                const Expanded(
                    child: Center(child: CircularProgressIndicator()))
              else if (_jobs == null || _jobs!.isEmpty)
                Expanded(
                  child: Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.inbox_rounded,
                            size: 64,
                            color: Colors.white.withValues(alpha: 0.1)),
                        const SizedBox(height: 16),
                        Text(
                          'No jobs in queue',
                          style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.3),
                              fontSize: 18),
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
                      border: Border.all(
                          color: Colors.white.withValues(alpha: 0.05)),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(24),
                      child: SingleChildScrollView(
                        child: DataTable(
                          headingRowColor: WidgetStateProperty.all(
                              const Color(0xFF222222)),
                          columns: [
                            DataColumn(
                              label: Checkbox(
                                value: _jobs != null &&
                                    _jobs!.isNotEmpty &&
                                    _selectedIds.length == _jobs!.length,
                                onChanged: (val) {
                                  setState(() {
                                    if (val == true) {
                                      _selectedIds.addAll(_jobs!
                                          .map((j) => j['id'] as String));
                                    } else {
                                      _selectedIds.clear();
                                    }
                                  });
                                },
                              ),
                            ),
                            const DataColumn(label: Text('Status')),
                            const DataColumn(label: Text('Source File')),
                            const DataColumn(label: Text('Attempts')),
                            const DataColumn(label: Text('Output')),
                          ],
                          rows: _jobs!.map((job) {
                            final id = job['id'] as String;
                            final status = job['status'] as String;
                            final source = job['source'] as String;
                            final attempts = job['attempts'] ?? 0;
                            final output = job['output'] as String;
                            final filename =
                                source.split('\\').last.split('/').last;
 
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
                              case 'skipped':
                                statusColor = Colors.white38;
                                statusIcon = Icons.skip_next_rounded;
                                break;
                            }
 
                            return DataRow(
                              selected: _selectedIds.contains(id),
                              onSelectChanged: (val) {
                                setState(() {
                                  if (val == true) {
                                    _selectedIds.add(id);
                                  } else {
                                    _selectedIds.remove(id);
                                  }
                                });
                              },
                              cells: [
                                DataCell(const SizedBox
                                    .shrink()), // Reserved for built-in checkbox
                                DataCell(
                                  Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(statusIcon,
                                          color: statusColor, size: 16),
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
                                DataCell(
                                  Tooltip(
                                    message: source,
                                    child: Text(filename,
                                        style: const TextStyle(fontSize: 12)),
                                  ),
                                ),
                                DataCell(Text(attempts.toString(),
                                    style: const TextStyle(fontSize: 12))),
                                DataCell(
                                  Tooltip(
                                    message: output,
                                    child: Text(
                                      output.split('\\').last.split('/').last,
                                      style: TextStyle(
                                          color: Colors.white
                                              .withValues(alpha: 0.4),
                                          fontSize: 12),
                                      overflow: TextOverflow.ellipsis,
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
              if (_isProcessing) _buildConsoleOverlay(),
            ],
          ),
        ),
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
