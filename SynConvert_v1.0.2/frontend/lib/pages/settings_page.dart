import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../backend_bridge.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  Map<String, dynamic>? _config;
  bool _isLoading = true;
  bool _isSaving = false;

  final TextEditingController _outputDirController = TextEditingController();
  final TextEditingController _namingTemplateController =
      TextEditingController();
  final TextEditingController _maxRetriesController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    setState(() => _isLoading = true);
    try {
      final bridge = context.read<BackendBridge>();
      final config = await bridge.getConfig();
      setState(() {
        _config = config;
        _outputDirController.text = config['output_dir'] ?? '';
        _namingTemplateController.text = config['naming_template'] ?? '';
        _maxRetriesController.text = (config['max_retries'] ?? 1).toString();
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _saveSettings() async {
    if (_config == null) return;
    setState(() => _isSaving = true);
    try {
      final bridge = context.read<BackendBridge>();
      final updates = {
        'output_dir': _outputDirController.text,
        'naming_template': _namingTemplateController.text,
        'max_retries': int.tryParse(_maxRetriesController.text) ?? 1,
        'default_preset': _config!['default_preset'],
        'review_before_convert': _config!['review_before_convert'],
        'skip_existing': _config!['skip_existing'],
        'force_encoder': _config!['force_encoder'],
      };
      await bridge.setConfig(updates);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Settings saved successfully'),
            backgroundColor: Color(0xFF2ECC71),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to save settings: $e'),
            backgroundColor: Colors.redAccent,
          ),
        );
      }
    } finally {
      setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Settings',
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 32),
          if (_isLoading)
            const Expanded(child: Center(child: CircularProgressIndicator()))
          else if (_config == null)
            Expanded(
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.error_outline_rounded,
                        size: 64, color: Colors.redAccent),
                    const SizedBox(height: 16),
                    const Text(
                      'Failed to load settings from backend',
                      style: TextStyle(color: Colors.white70, fontSize: 18),
                    ),
                    const SizedBox(height: 24),
                    ElevatedButton(
                      onPressed: _loadSettings,
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            )
          else
            Expanded(
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildSectionHeader('General'),
                    _buildTextField(
                      'Output Directory',
                      _outputDirController,
                      'Default folder for converted videos.',
                    ),
                    const SizedBox(height: 24),
                    _buildTextField(
                      'Naming Template',
                      _namingTemplateController,
                      'e.g. S{S:02d}E{E:02d} - {title}',
                    ),
                    const SizedBox(height: 32),
                    _buildSectionHeader('Conversion'),
                    _buildSwitchTile(
                      'Review before conversion',
                      'Show a mapping of files before starting the process.',
                      _config!['review_before_convert'] as bool,
                      (val) => setState(
                        () => _config!['review_before_convert'] = val,
                      ),
                    ),
                    _buildSwitchTile(
                      'Skip existing files',
                      'Do not re-convert files that already exist in the output folder.',
                      _config!['skip_existing'] as bool,
                      (val) => setState(() => _config!['skip_existing'] = val),
                    ),
                    const SizedBox(height: 16),
                    _buildTextField(
                      'Max Retries',
                      _maxRetriesController,
                      'Number of attempts per file if FFmpeg fails.',
                      width: 150,
                    ),
                    const SizedBox(height: 24),
                    _buildDropdown(
                      'Default Resolution',
                      _config!['default_preset'],
                      const {
                        '720p_mobile': '720p Mobile (Recommended)',
                        '480p_saver': '480p Storage Saver',
                      },
                      (val) => setState(() => _config!['default_preset'] = val),
                    ),
                    const SizedBox(height: 40),
                    ElevatedButton.icon(
                      onPressed: _isSaving ? null : _saveSettings,
                      icon: _isSaving
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.save_rounded),
                      label: const Text('Save Settings'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF00D2FF),
                        foregroundColor: Colors.black,
                        minimumSize: const Size(200, 56),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: Text(
        title.toUpperCase(),
        style: const TextStyle(
          color: Color(0xFF00D2FF),
          fontWeight: FontWeight.bold,
          fontSize: 12,
          letterSpacing: 1.2,
        ),
      ),
    );
  }

  Widget _buildTextField(
    String label,
    TextEditingController controller,
    String hint, {
    double? width,
  }) {
    return Container(
      width: width ?? 600,
      margin: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: controller,
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.2)),
              filled: true,
              fillColor: const Color(0xFF161616),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide.none,
              ),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 16,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDropdown(
    String label,
    String value,
    Map<String, String> options,
    Function(String) onChanged,
  ) {
    return Container(
      width: 600,
      margin: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(
              color: const Color(0xFF161616),
              borderRadius: BorderRadius.circular(12),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: value,
                isExpanded: true,
                dropdownColor: const Color(0xFF161616),
                style: const TextStyle(color: Colors.white),
                items: options.entries.map((e) {
                  return DropdownMenuItem(
                    value: e.key,
                    child: Text(e.value),
                  );
                }).toList(),
                onChanged: (val) {
                  if (val != null) onChanged(val);
                },
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSwitchTile(
    String title,
    String subtitle,
    bool value,
    Function(bool) onChanged,
  ) {
    return Container(
      width: 600,
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF161616),
        borderRadius: BorderRadius.circular(12),
      ),
      child: SwitchListTile(
        title: Text(
          title,
          style: const TextStyle(color: Colors.white, fontSize: 14),
        ),
        subtitle: Text(
          subtitle,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.4),
            fontSize: 12,
          ),
        ),
        value: value,
        onChanged: onChanged,
        activeThumbColor: const Color(0xFF00D2FF),
      ),
    );
  }
}
