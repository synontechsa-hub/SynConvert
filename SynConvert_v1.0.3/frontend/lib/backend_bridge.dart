import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as p;

/// Represents the status of the Python backend environment.
enum BackendStatus {
  ready,
  pythonMissing,
  moduleMissing,
  error,
}

/// A single file conversion proposal returned by the backend scan.
class ScanProposal {
  final String source;
  final String relative;
  final String outputFilename;
  final int season;
  final int episode;
  final String title;

  ScanProposal({
    required this.source,
    required this.relative,
    required this.outputFilename,
    required this.season,
    required this.episode,
    required this.title,
  });

  factory ScanProposal.fromJson(Map<String, dynamic> json) {
    return ScanProposal(
      source: json['source'] as String,
      relative: json['relative'] as String,
      outputFilename: json['output_filename'] as String,
      season: json['season'] as int,
      episode: json['episode'] as int,
      title: json['title'] as String,
    );
  }
}

/// The bridge between Flutter and the Python SynConvert backend.
class BackendBridge {
  static final BackendBridge _instance = BackendBridge._internal();
  factory BackendBridge() => _instance;
  BackendBridge._internal();

  Process? _activeProcess;

  String get _backendRoot {
    final envRoot = Platform.environment['SYNCONVERT_ROOT'];
    if (envRoot != null && envRoot.isNotEmpty) {
      return envRoot;
    }

    final exeDir = File(Platform.resolvedExecutable).parent;
    Directory dir = exeDir;
    for (int i = 0; i < 6; i++) {
      final venv = Directory(p.join(dir.path, '.venv'));
      if (venv.existsSync()) return dir.path;
      final parent = dir.parent;
      if (parent.path == dir.path) break;
      dir = parent;
    }

    return Directory.current.path;
  }

  String get _pythonPath {
    final root = _backendRoot;
    if (Platform.isWindows) {
      return p.join(root, '.venv', 'Scripts', 'python.exe');
    }
    return p.join(root, '.venv', 'bin', 'python');
  }

  Map<String, String> get _pythonEnv => {
        ...Platform.environment,
        'PYTHONIOENCODING': 'utf-8',
        'PYTHONUTF8': '1',
      };

  Future<BackendStatus> checkStatus() async {
    try {
      final result = await Process.run(
        _pythonPath,
        ['-u', '-m', 'backend.main', '--help'],
        workingDirectory: _backendRoot,
        environment: _pythonEnv,
        stdoutEncoding: utf8,
        stderrEncoding: utf8,
      );
      if (result.exitCode == 0) return BackendStatus.ready;

      if (result.stderr.toString().contains('No module named backend')) {
        return BackendStatus.moduleMissing;
      }
      return BackendStatus.error;
    } catch (e) {
      return BackendStatus.pythonMissing;
    }
  }

  Future<Map<String, dynamic>> getConfig() async {
    final result = await Process.run(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'config', '--get'],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
      stdoutEncoding: utf8,
    );

    if (result.exitCode != 0) {
      throw Exception('Failed to get config: ${result.stderr}');
    }

    return jsonDecode(result.stdout as String) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> getAvailableEncoders() async {
    final result = await Process.run(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'encoders'],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
      stdoutEncoding: utf8,
    );

    if (result.exitCode != 0) {
      throw Exception('Failed to get encoders: ${result.stderr}');
    }

    final List<dynamic> list = jsonDecode(result.stdout as String);
    return list.map((e) => e as Map<String, dynamic>).toList();
  }

  Future<void> setConfig(Map<String, dynamic> config) async {
    final configJson = jsonEncode(config);
    final result = await Process.run(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'config', '--set', configJson],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
      stdoutEncoding: utf8,
    );

    if (result.exitCode != 0) {
      throw Exception('Failed to set config: ${result.stderr}');
    }
  }

  /// Forcefully stop the active conversion process and clean up FFmpeg.
  Future<void> stopActiveProcess() async {
    // 1. Kill the Python backend process if it's running
    _activeProcess?.kill();
    _activeProcess = null;

    // 2. Kill any orphaned FFmpeg processes (Windows specific)
    if (Platform.isWindows) {
      await Process.run('taskkill', ['/F', '/IM', 'ffmpeg.exe', '/T']);
    }
  }

  Future<void> clearCompletedJobs() async {
    final result = await Process.run(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'queue', '--clear-done'],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
    );
    if (result.exitCode != 0) {
      throw Exception('Failed to clear queue: ${result.stderr}');
    }
  }

  Future<void> resetFailedJobs() async {
    final result = await Process.run(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'queue', '--reset-failed'],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
    );
    if (result.exitCode != 0) {
      throw Exception('Failed to reset queue: ${result.stderr}');
    }
  }

  Stream<String> resumeQueue() async* {
    _activeProcess = await Process.start(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'queue', '--resume'],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
    );
    final process = _activeProcess!;

    final controller = StreamController<String>();

    final stdoutSub = process.stdout
        .transform(Utf8Decoder(allowMalformed: true))
        .transform(const LineSplitter())
        .listen(controller.add, onError: controller.addError);

    final stderrSub = process.stderr
        .transform(Utf8Decoder(allowMalformed: true))
        .transform(const LineSplitter())
        .listen(controller.add, onError: controller.addError);

    Future.wait([stdoutSub.asFuture(), stderrSub.asFuture()]).then((_) async {
      await process.exitCode;
      await controller.close();
    });

    yield* controller.stream;
  }

  Future<List<Map<String, dynamic>>> getQueueStatus() async {
    final result = await Process.run(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'status', '--json'],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
      stdoutEncoding: utf8,
    );

    if (result.exitCode != 0) {
      return [];
    }

    final List<dynamic> data = jsonDecode(result.stdout as String);
    return data.cast<Map<String, dynamic>>();
  }

  Future<List<ScanProposal>> scanDirectory(String inputPath) async {
    final result = await Process.run(
      _pythonPath,
      ['-u', '-m', 'backend.main', 'scan', '--input', inputPath, '--json'],
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
      stdoutEncoding: utf8,
      stderrEncoding: utf8,
    );

    if (result.exitCode != 0) {
      throw Exception('Scan failed: ${result.stderr}');
    }

    final List<dynamic> data = jsonDecode(result.stdout as String);
    return data
        .map((item) => ScanProposal.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Stream<String> convert({
    required String input,
    required String output,
    String? preset,
    bool review = false,
  }) async* {
    final args = [
      '-u', '-m', 'backend.main', 'convert',
      '--input', input,
      '--output', output,
    ];

    if (preset != null) args.addAll(['--preset', preset]);
    if (!review) args.add('--no-review');

    _activeProcess = await Process.start(
      _pythonPath,
      args,
      workingDirectory: _backendRoot,
      environment: _pythonEnv,
    );
    final process = _activeProcess!;

    final controller = StreamController<String>();

    final stdoutSub = process.stdout
        .transform(Utf8Decoder(allowMalformed: true))
        .transform(const LineSplitter())
        .listen(controller.add, onError: controller.addError);

    final stderrSub = process.stderr
        .transform(Utf8Decoder(allowMalformed: true))
        .transform(const LineSplitter())
        .listen(controller.add, onError: controller.addError);

    Future.wait([stdoutSub.asFuture(), stderrSub.asFuture()]).then((_) async {
      final exitCode = await process.exitCode;
      if (exitCode != 0) {
        controller.add('Process exited with error code $exitCode');
      }
      await controller.close();
    });

    yield* controller.stream;
  }
}
