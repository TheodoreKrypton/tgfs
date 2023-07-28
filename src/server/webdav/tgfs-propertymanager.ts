import {
  Errors,
  IPropertyManager,
  PropertyAttributes,
  PropertyBag,
  ResourcePropertyValue,
  Return2Callback,
  ReturnCallback,
  SimpleCallback,
} from 'webdav-server/lib/index.v2';

export class TGFSPropertyManager implements IPropertyManager {
  properties: PropertyBag = {};

  constructor(serializedData?: any) {
    if (serializedData)
      for (const name in serializedData) this[name] = serializedData[name];
  }

  setProperty(
    name: string,
    value: ResourcePropertyValue,
    attributes: PropertyAttributes,
    callback: SimpleCallback,
  ): void {
    this.properties[name] = {
      value,
      attributes,
    };
    callback(null);
  }

  getProperty(
    name: string,
    callback: Return2Callback<ResourcePropertyValue, PropertyAttributes>,
  ): void {
    const property = this.properties[name];
    console.log(property);
    callback(
      property ? null : Errors.PropertyNotFound,
      property.value,
      property.attributes,
    );
  }

  removeProperty(name: string, callback: SimpleCallback): void {
    delete this.properties[name];
    callback(null);
  }

  getProperties(
    callback: ReturnCallback<PropertyBag>,
    byCopy: boolean = false,
  ): void {
    callback(
      null,
      byCopy ? this.properties : JSON.parse(JSON.stringify(this.properties)),
    );
  }
}
