export type IInType = 'boolean'|'number'|'string'|'array'|'object'|'json';

interface IItem {
  id: string
  title: string;
  type: IInType;
  required: boolean;
  description: string;
  property: string;
  prop: string;
  default: any;
  isAdd: boolean;
  'ui:component': {
    name: string;
    prop: { [key: string]: any };
  };
  properties: IItem;
}

export interface Doll {
  id: string
  type: IInType;

  // formItem
  prop: string;
  title: string; // label & prototype
  property: string; // demo a.0.b.c.2.3
  required: boolean;
  description: string;
  rules?: any[];
  children?: Doll[];

  // 附加的属性
  addAble: boolean; // object array
  deleteAble: boolean; // object array
  convertible: boolean; // 可转换 try JSON.parse // todo
  level: number; // 限制层级深度

  // 表单组件
  component: string;
  props: { [key: string]: any };
  defaultValue: any;

  schema?: any // 原始的配置
  newSchema?: any // 新的配置 todo
}

const lowerStr = 'abcdefghijklmnopqrstuvwxyz0123456789';

export const uuid = (n = 10, str = lowerStr): string => {
  let result = str[parseInt((Math.random() * str.length).toString(), 10)];
  for (let i = 1; i < n; i++) {
    result += str[parseInt((Math.random() * str.length).toString(), 10)];
  }
  return result;
};

const complexType = ['array', 'object'];
const bfArrayTitle = ['labels', '标签'];
const bfArrayKey = 'key';
const bfArrayValue = 'value';

function getDefaultValue(params) {
  if (params.default) {
    return params.default;
  }
  const { type } = params;
  if (['number', 'string'].includes(type)) {
    return '';
  }
  if (type === 'boolean') {
    return false;
  }
  if (type === 'array') {
    return [];
  }
  return {};
};

function getDefaultComponent(params: IItem) {
  const { type, 'ui:component': component = {} } = params;
  let realComponent = component.name;
  if (type === 'array') {
    const { title, items: { properties = {} } } = params;
    const propKeys = bfArrayTitle.some(t => title.includes(t)) ? Object.keys(properties) : [];
    if (propKeys.length === 2 && [bfArrayKey, bfArrayValue].every(key => propKeys.includes(key))) {
      realComponent = 'bfArray';
    }
  } else {
    realComponent = type === 'boolean' ? 'bk-checkbox'  : 'bk-input';
  }
  return realComponent;
};

function getDefaultProps(params: IItem) {
  const { 'ui:component': component = {}, type } = params;
  const prop = component.prop || {};
  if (type === 'number') {
    prop.type = 'number';
  }
  return prop;
};

export function getRules(schema) {
  return schema.required
    ? [
      {
        required: true,
        message: window.i18n.t ? window.i18n.t('必填项') : '必填项',
        trigger: 'blur',
      },
    ]
    : [];
}
export function getAddAble(schema: IItem) {
  return complexType.includes(schema.type);
}
export function getDeleteAble(schema: IItem) {
  return complexType.includes(schema.type);
}
export function getConvertible(schema: IItem) {
  return complexType.includes(schema.type) && !schema.required;
}

export const getRealProp = (parentProp?: string, prop: string): string => (parentProp ? `${parentProp}.${prop}` : prop);

export function formatSchema(schema: IItem, parentProp = '', level = 0, key?: string): Doll {
  const { type = 'string', properties = {} } = schema;
  const prop = key ? key : schema.prop || schema.title;
  const property = parentProp ? `${parentProp}.${prop}` : prop;
  // console.log(parentProp, '+', prop, '=', property);
  const baseItem: Doll = {
    id: uuid(),
    type,

    // formItem
    prop,
    title: schema.title || prop,
    property,
    parentProp,
    required: !!schema.required,
    description: schema.description || '',
    rules: getRules(schema),
    children?: null,

    // 附加的属性
    addAble: getAddAble(schema),
    deleteAble: getDeleteAble(schema),
    convertible: getConvertible(schema),
    level,

    // 表单组件
    component: getDefaultComponent(schema),
    props: getDefaultProps(schema),
    defaultValue: getDefaultValue(schema),

    schema, // 原始的配置
    newSchema: {}, // 新的配置 todo
  };
  if (complexType.includes(type)) {
    const newLevel = level + 1;
    if (type === 'array') {
      baseItem.children = [formatSchema(schema.items || {}, `${property}`, newLevel)];
      // properties = schema.items || {}
    } else {
      baseItem.children = Object.keys(properties).map(key => formatSchema(Object.assign({ title: key }, { ...properties[key] }), `${property}`, newLevel, key));
    }
    // console.log(property, 'cccccccc');
  }
  return baseItem;
}

export function initSchema(schema: IItem): Doll[] {
  // const list: Doll[] = []
  // if (Array.isArray(schema)) {
  //   schema.map((item, index) => list
  // .push(initSchema(item, `${parentProp ? parentProp + '' + index : index}`, level)))
  //   return list
  //   // return schema
  // .map((item, index) => initSchema(item, `${parentProp ? parentProp + '' + index : index}`, level));
  // }
  // console.log(schema.property)
  return formatSchema(schema);
  // return formatSchema(schema, schema.property)
}

export const transformSchema = (schema: any, parentRequired: any[] = [], key: string = '') => {
  if (!schema || typeof schema !== 'object') return schema;

  // 处理对象类型的属性
  if (schema.type === 'object' && schema.properties) {
    const requiredProps = [];
    for (const key in schema.properties) {
      const prop = schema.properties[key];
      if (typeof prop.required !== 'undefined') {
        if (prop.required) {
          requiredProps.push(key);
          if (prop.type === 'array') {
            prop['minItems'] = 1;
            prop['ui:group'] = {
              "props": {
                "verifiable": false,
              },
            };
          }
          prop['ui:rules'] = ['required']; // 增加 ui:rules
        }
        // 删除所有的 required，无论是 true 还是 false
        delete prop.required;
      }
      // 递归处理子属性
      transformSchema(prop, requiredProps, key);
    }
    if (schema.required !== undefined) {
      if (schema.required) {
        parentRequired.push(key);
      }
      // 处理对象类型中的 required 属性
      delete schema.required;
    }
    
    if (requiredProps.length > 0) {
      schema.required = requiredProps;
    }
  }

  // 处理数组类型的项
  if (schema.type === 'array' && schema.items) {
    const itemRequiredProps: any = [];
    // 递归处理数组的每个项
    transformSchema(schema.items, itemRequiredProps, key);
    if (schema.required !== undefined) {
      delete schema.required; // 删除数组项中的 required
    }
    // 不展示组校验
    schema['ui:group'] = {
      "props": {
        "verifiable": false,
      },
    };
    // 添加样式修改
    schema['ui:props'] = {
      "size": 'large'
    };
    // 处理描述信息
    if (schema.description) {
      schema['ui:group']['props']['description'] = schema.description;
    }
    if (schema.items.properties && Object.keys(schema.items.properties).length >= 2) {
      // 如果是 key 和 value，添加 ui:component
      if (schema.items.properties.key && schema.items.properties.value) {
        schema['ui:component'] = { "name": "bfArray" };
      }
      schema.items['ui:group'] = {
        "props": {
          "type": "card",
        },
        "style": {
          "background": "#F5F7FA",
        },
      };
    }
    if (schema.items.type === 'string' || schema.items.type === 'boolean' || schema.items.type === 'integer') {
      // parentRequired.push(key);
    }
  }

  // 转换 ui_component 属性到 ui:component
  if (schema.ui_component && schema.ui_component.type === 'select') {
    const datasource = [];
    for (const optionKey in schema.ui_component.properties) {
      const option = schema.ui_component.properties[optionKey];
      datasource.push({
        label: option.title,
        value: option.value
      });
    }
    schema['ui:component'] = {
      name: 'select',
      props: {
        datasource,
        clearable: false
      }
    };
    delete schema.ui_component; // 删除原始的 ui_component
  }
  
  // 处理字符串、布尔和整数类型的属性，删除 required
  if (schema.type === 'string' || schema.type === 'boolean' || schema.type === 'integer') {
    if (schema.required !== undefined) {
      if (schema.required) {
        schema['ui:rules'] = ['required'];
      }
      // 删除 required
      delete schema.required;
    }
  }

  return schema;
}
export const createItem = (property: string, params: IItem, id?: string): Doll => {
  console.log('property: ', property, params.type, '; params: ', params);
  return {
    id: id || uuid(),
    ...Object.assign({
      property,
      type: 'string',
      required: false,
      readonly: false,
      description: '',
      // default: getDefaultValue(params),
      defautlC: getDefaultValue(params),
      component: getDefaultComponent(params),
      prop: getDefaultProps(params),
      isAdd: false,
      removeAble: false,
      convertible: false,
    }, params),
  };
};
