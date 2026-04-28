import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:provider/provider.dart';
import '../backend_bridge.dart';

class WizardPage extends StatefulWidget {
  const WizardPage({super.key});

  @override
  State<WizardPage> createState() => _WizardPageState();
}

class _WizardPageState extends State<WizardPage> {
  String? _inputPath;
  String? _outputPath;
  List<ScanProposal>? _proposals;
  bool _isScanning = false;
  bool _isConverting = false;
  final List<String> _conversionLog = [];

  Future<void> _pickInputFolder() async {
    // FIX: FilePicker.platform is deprecated in file_picker v5+
    // Use FilePicker.instance instead
    final result = await FilePicker.instance.getDirectoryPath(
      dialogTitle: 'Select Source Folder',
    );
    if (result != null) {
      setState(() {
        _inputPath = result;
        _proposals = null;
        _conversionLog.clear();
      });
      _runScan();
    }
  }

  Future<void> _pickOutputFolder() async {
    final result = await FilePicker.instance.getDirectoryPath(
      dialogTitle: 'Select Output Folder',
    );
    if (result != null) {
      setState(() => _outputPath = result);
    }
  }

  Future<void> _runScan() async {
    if (_inputPath == null) return;

    setState(() => _isScanning = true);
    try {
      final bridge = context.read<BackendBridge>();
      final results = await bridge.scanDirectory(_inputPath!);
      setState(() {
        _proposals = results;
        _isScanning = false;
      });
    } catch (e) {
      setState(() => _isScanning = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Scan failed: $e'),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    }
  }

  Future<void> _startConversion() async {
    if (_inputPath == null || _outputPath == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please select both a source and output folder.'),
          backgroundColor: Colors.orangeAccent,
        ),
      );
      return;
    }

    setState(() {
      _isConverting = true;
      _conversionLog.clear();
    });

    try {
      final bridge = context.read<BackendBridge>();
      final stream = bridge.convert(
        input: _inputPath!,
        output: _outputPath!,
        review: false,
      );

      await for (final line in stream) {
        if (mounted) {
          setState(() => _conversionLog.add(line));
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() => _conversionLog.add('Error: $e'));
      }
    } finally {
      if (mounted) setState(() => _isConverting = false);
    }
  }

  void _reset() {
    setState(() {
      _inputPath = null;
      _outputPath = null;
      _proposals = null;
      _conversionLog.clear();
      _isConverting = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'New Conversion Job',
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
          ),
          const SizedBox(height: 32),
          if (_inputPath == null)
            _buildFolderPicker()
          else if (_isScanning)
            const Expanded(
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_isConverting)
            Expanded(child: _buildConversionLog())
          else if (_proposals != null)
            Expanded(child: _buildProposalTable())
          else
            const Center(child: Text('Unexpected state')),
        ],
      ),
    );
  }

  Widget _buildFolderPicker() {
    return Expanded(
      child: Center(
        child: Container(
          width: 500,
          padding: const EdgeInsets.all(48),
          decoration: BoxDecoration(
            color: const Color(0xFF161616),
            borderRadius: BorderRadius.circular(32),
            // FIX: withOpacity deprecated — use withValues(alpha:)
            border: Border.all(
              color: Colors.white.withValues(alpha: 0.05),
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: const Color(0xFF00D2FF).withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.folder_open_rounded,
                  color: Color(0xFF00D2FF),
                  size: 48,
                ),
              ),
              const SizedBox(height: 32),
              const Text(
                'Select Source Folder',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Pick the directory containing your anime or videos.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white.withValues(alpha: 0.5)),
              ),
              const SizedBox(height: 40),
              ElevatedButton(
                onPressed: _pickInputFolder,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF00D2FF),
                  foregroundColor: Colors.black,
                  minimumSize: const Size(double.infinity, 56),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                  ),
                  elevation: 0,
                ),
                child: const Text(
                  'Browse Folders',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildProposalTable() {
    return Column(
      children: [
        // Header row
        Row(
          children: [
            const Icon(Icons.check_circle_outline, color: Color(0xFF00D2FF)),
            const SizedBox(width: 12),
            Text(
              'Discovered ${_proposals!.length} files. Review the naming below.',
              style: const TextStyle(color: Colors.white, fontSize: 16),
            ),
            const Spacer(),
            TextButton.icon(
              onPressed: _reset,
              icon: const Icon(Icons.refresh_rounded),
              label: const Text('Change Folder'),
            ),
          ],
        ),
        const SizedBox(height: 16),

        // Output folder selector
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: const Color(0xFF161616),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: _outputPath != null
                  ? const Color(0xFF00D2FF).withValues(alpha: 0.4)
                  : Colors.white.withValues(alpha: 0.05),
            ),
          ),
          child: Row(
            children: [
              Icon(
                Icons.drive_folder_upload_rounded,
                color: _outputPath != null
                    ? const Color(0xFF00D2FF)
                    : Colors.white.withValues(alpha: 0.4),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _outputPath ?? 'No output folder selected',
                  style: TextStyle(
                    color: _outputPath != null
                        ? Colors.white
                        : Colors.white.withValues(alpha: 0.4),
                    fontSize: 13,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              TextButton(
                onPressed: _pickOutputFolder,
                child: Text(
                  _outputPath != null ? 'Change' : 'Select Output',
                  style: const TextStyle(color: Color(0xFF00D2FF)),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Proposal table
        Expanded(
          child: Container(
            decoration: BoxDecoration(
              color: const Color(0xFF161616),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.05),
              ),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(24),
              child: SingleChildScrollView(
                child: DataTable(
                  // FIX: MaterialStateProperty deprecated — use WidgetStateProperty
                  headingRowColor: WidgetStateProperty.all(
                    const Color(0xFF222222),
                  ),
                  columns: const [
                    DataColumn(label: Text('Source')),
                    DataColumn(label: Text('Season')),
                    DataColumn(label: Text('Episode')),
                    DataColumn(label: Text('Output Name')),
                  ],
                  rows: _proposals!
                      .map(
                        (p) => DataRow(
                          cells: [
                            DataCell(Text(
                              p.relative,
                              style: const TextStyle(fontSize: 12),
                            )),
                            DataCell(Text(
                              'S${p.season.toString().padLeft(2, '0')}',
                            )),
                            DataCell(Text(
                              'E${p.episode.toString().padLeft(2, '0')}',
                            )),
                            DataCell(Text(
                              p.outputFilename,
                              style: const TextStyle(
                                color: Color(0xFF00D2FF),
                              ),
                            )),
                          ],
                        ),
                      )
                      .toList(),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 24),

        // Action row
        Row(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            ElevatedButton(
              // FIX: was a TODO no-op — now wired to _startConversion()
              onPressed: _outputPath != null ? _startConversion : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF00D2FF),
                foregroundColor: Colors.black,
                disabledBackgroundColor: const Color(0xFF00D2FF).withValues(alpha: 0.3),
                minimumSize: const Size(200, 56),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
              ),
              child: Text(
                _outputPath != null ? 'Start Conversion' : 'Select Output First',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildConversionLog() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(width: 12),
            const Text(
              'Converting...',
              style: TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Expanded(
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF0A0A0A),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
            ),
            child: ListView.builder(
              itemCount: _conversionLog.length,
              itemBuilder: (context, index) {
                final line = _conversionLog[index];
                Color lineColor = Colors.white.withValues(alpha: 0.7);
                if (line.contains('✓') || line.contains('success')) {
                  lineColor = const Color(0xFF2ECC71);
                } else if (line.contains('✗') || line.contains('failed') || line.contains('Error')) {
                  lineColor = Colors.redAccent;
                } else if (line.contains('⟳') || line.contains('Retry')) {
                  lineColor = Colors.orangeAccent;
                }
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Text(
                    line,
                    style: TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 12,
                      color: lineColor,
                    ),
                  ),
                );
              },
            ),
          ),
        ),
      ],
    );
  }
}
