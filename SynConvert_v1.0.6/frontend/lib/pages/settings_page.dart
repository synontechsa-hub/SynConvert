import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../backend_bridge.dart';
import '../services/theme_provider.dart';

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
  List<Map<String, dynamic>> _availableEncoders = [];
  bool _isLoading = true;
  bool _isSaving = false;

  String _selectedRes = '720p';
  String _selectedQuality = 'medium';

  final TextEditingController _outputDirController = TextEditingController();
  final TextEditingController _namingTemplateController =
      TextEditingController();
  final TextEditingController _maxRetriesController = TextEditingController();
  final TextEditingController _parallelJobsController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    setState(() => _isLoading = true);
    try {
      final bridge = context.read<BackendBridge>();
      debugPrint('Fetching config...');
      final config = await bridge.getConfig();
      debugPrint('Fetching encoders...');
      final encoders = await bridge.getAvailableEncoders();
      
      setState(() {
        _config = config;
        _availableEncoders = encoders;
        _outputDirController.text = config['output_dir'] ?? '';
        _namingTemplateController.text = config['naming_template'] ?? '';
        _maxRetriesController.text = (config['max_retries'] ?? 1).toString();
        _parallelJobsController.text = (config['parallel_jobs'] ?? 1).toString();

        final preset = config['default_preset'] as String? ?? '720p_medium';
        final parts = preset.split('_');
        if (parts.length == 2) {
          _selectedRes = parts[0];
          
          final rawQuality = parts[1];
          if (rawQuality == 'mobile') {
            _selectedQuality = 'medium';
          } else if (rawQuality == 'saver') {
            _selectedQuality = 'low';
          } else if (['high', 'medium', 'low'].contains(rawQuality)) {
            _selectedQuality = rawQuality;
          } else {
            _selectedQuality = 'medium';
          }
        } else {
          _selectedRes = '720p';
          _selectedQuality = 'medium';
        }

        _isLoading = false;
      });
    } catch (e) {
      debugPrint('❌ Settings Load Error: $e');
      if (mounted) {
        setState(() {
          _isLoading = false;
          _config = null; // Ensure we show the error state
        });
      }
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
        'parallel_jobs': int.tryParse(_parallelJobsController.text) ?? 1,
        'show_notifications': _config!['show_notifications'] ?? true,
        'default_preset': '${_selectedRes}_$_selectedQuality',
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
              color: Theme.of(context).colorScheme.onSurface,
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
                    Text(
                      'Failed to load settings from backend',
                      style: TextStyle(color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.7), fontSize: 18),
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
                    _buildThemeDropdown(),
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
                    _buildSwitchTile(
                      'System Notifications',
                      'Show a Windows notification when a batch finishes.',
                      _config!['show_notifications'] as bool? ?? true,
                      (val) => setState(() => _config!['show_notifications'] = val),
                    ),
                    const SizedBox(height: 16),
                    _buildTextField(
                      'Max Retries',
                      _maxRetriesController,
                      'Number of attempts per file if FFmpeg fails.',
                      width: 150,
                    ),
                    _buildTextField(
                      'Parallel Jobs',
                      _parallelJobsController,
                      'Number of files to convert simultaneously (1-4).',
                      width: 150,
                    ),
                    _buildDropdown(
                      'Default Resolution',
                      _selectedRes,
                      const {
                        '1080p': '1080p (Full HD)',
                        '720p': '720p (HD)',
                        '480p': '480p (SD)',
                      },
                      (val) => setState(() => _selectedRes = val),
                    ),
                    const SizedBox(height: 16),
                    _buildDropdown(
                      'Default Quality',
                      _selectedQuality,
                      const {
                        'high': 'High (Best Quality)',
                        'medium': 'Medium (Balanced)',
                        'low': 'Low (Smallest Size)',
                      },
                      (val) => setState(() => _selectedQuality = val),
                    ),
                    const SizedBox(height: 32),
                    _buildSectionHeader('Hardware'),
                    _buildDropdown(
                      'Preferred GPU / Encoder',
                      _config!['force_encoder'] ?? '',
                      {
                        '': 'Auto-Detect (Best Available)',
                        for (var e in _availableEncoders)
                          e['video_encoder'] as String: e['label'] as String,
                      },
                      (val) => setState(() {
                        _config!['force_encoder'] = val == '' ? null : val;
                      }),
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
            style: TextStyle(
              color: Theme.of(context).colorScheme.onSurface,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: controller,
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: TextStyle(color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.2)),
              filled: true,
              fillColor: Theme.of(context).cardColor,
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
            style: TextStyle(
              color: Theme.of(context).colorScheme.onSurface,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(
              color: Theme.of(context).cardColor,
              borderRadius: BorderRadius.circular(12),
            ),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: value,
                isExpanded: true,
                dropdownColor: Theme.of(context).cardColor,
                style: TextStyle(color: Theme.of(context).colorScheme.onSurface),
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
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(12),
      ),
      child: SwitchListTile(
        title: Text(
          title,
          style: TextStyle(color: Theme.of(context).colorScheme.onSurface, fontSize: 14),
        ),
        subtitle: Text(
          subtitle,
          style: TextStyle(
            color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.4),
            fontSize: 12,
          ),
        ),
        value: value,
        onChanged: onChanged,
        activeThumbColor: const Color(0xFF00D2FF),
      ),
    );
  }
  Widget _buildThemeDropdown() {
    final themeProvider = context.watch<ThemeProvider>();
    return _buildDropdown(
      'Application Theme',
      themeProvider.themeMode.toString().split('.').last,
      const {
        'system': 'System Default',
        'light': 'Light Mode',
        'dark': 'Dark Mode',
      },
      (val) {
        ThemeMode mode;
        if (val == 'light') {
          mode = ThemeMode.light;
        } else if (val == 'dark') {
          mode = ThemeMode.dark;
        } else {
          mode = ThemeMode.system;
        }
        themeProvider.setTheme(mode);
      },
    );
  }
}

