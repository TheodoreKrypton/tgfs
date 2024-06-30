import { PassThrough, TransformOptions } from 'stream';

export class UploadStream extends PassThrough {
  constructor(options?: TransformOptions) {
    super(options);

    this.on('end', () => {});
  }

  finish() {
    this.emit('finish');
  }
}
