<template>
    <div
        class="edit-tag"
        :class="{ shortcut }"
        @click.stop="">
        <div
            v-if="!isEditing"
            class="render-value-box"
            @click.stop="handleTextClick">
            <div
                ref="content"
                v-bk-overflow-tips
                class="value-text"
                tag-edit-tag>
                <slot>
                    <template v-if="flexibleTags.length">
                        <FlexibleTag :list="flexibleTags" />
                    </template>
                    <span v-else>--</span>
                </slot>
            </div>
            <template v-if="!isLoading">
                <div
                    v-if="shortcut"
                    class="tag-shortcut-box"
                    @click.stop="">
                    <div class="shortcut-action-btn">
                        <i
                            v-bk-tooltips="$t('复制')"
                            class="option-icon nodeman-icon nc-windows"
                            @click="handleCopy">
                        </i>
                        <i
                            v-bk-tooltips="$t('粘贴')"
                            class="option-icon nodeman-icon nc-windows"
                            @click="handlePaste" >
                        </i>
                    </div>
                </div>
            </template>
            <icon v-if="isLoading"  class="tag-edit-loading" type="loading-circle" />
        </div>
        <div v-else class="edit-value-box">
            <bk-tag-input
                ref="tagInputRef"
                searchable
                has-delete-icon
                use-group
                trigger="focus"
                :list="options"
                :placeholder="$t('请输入或选择')"
                :tag-tpl="tagTpl"
                v-model="localValue"
                :collapse-tags="true"
                :filter-callback="filterData"
                @blur="handleBlur"
                @change="handleChange"
                @inputchange="handleInputchange" />
                <div class="create-tag-pop" v-if="popShow"  @click="createTag">
                    <div class="create-tag-box">
                        <i18n path="新建标签" class="create-tag">
                            <span>{{ tag }}</span>
                        </i18n>
                    </div>
                </div>
        </div>
    </div>
</template>
<script lang="ts">
interface Tag {
    name: string,
    description: string,
    className: string
}
import i18n from '@/setup';
import { computed, defineComponent, getCurrentInstance, ref, toRefs, reactive, watch, PropType, onMounted, nextTick } from 'vue';
import FlexibleTag from '@/components/common/flexible-tag.vue';
import { IPkgTagOpt, PkgType} from '@/types/agent/pkg-manage';
import { AgentStore } from '@/store';

const copyMemo = ref([]);
export default defineComponent ({
    name: 'EditTag',
    components: {
        FlexibleTag,
    },
    props: {
        field: {
            type: String,
            required: true,
        },
        value: {
            type: Array,
            default: () => [],
        },
        // 显示复制粘贴按钮
        shortcut: {
            type: Boolean,
            default: false,
        },
        remoteHander: {
            type: Function,
            default: () => Promise.resolve(),
        },
        rules: {
            type: Array,
            default: () => [],
        },
        // 下拉框数据源
        options: {
            type: Array,
            default: () => ([]),
        },
        active: {
            type: String as PropType<PkgType>,
            default: 'gse_agent',
        }
    },
    emits: ['paste', 'editTag'],
    setup(props, { emit }) {
        const { proxy } = (getCurrentInstance() || {});
        const isEditing = ref(false);
        const isLoading = ref(false);
        const localValue = ref<string[]>(props.value.map((item :any) => item.className === '' ? item.name : item.className));
        const flexibleTags = ref(props.value); //用于展示的标签列表，带有className
        watch(()=> props.value, (val) => {
            flexibleTags.value = val;
        });
        const tag = ref<any>();
        
        const state = reactive<{
            value: string[];
            popShow: boolean; // 输入未匹配标签时候展示
        }>({
            value: [],
            popShow: false,
        });

        const tagTpl = (opt: IPkgTagOpt) => proxy?.$createElement('div', {
            class: `tag ${opt.className}`,
        }, [
            proxy?.$createElement('span', { class: 'text' }, opt.name),
        ]);
        onMounted(() => {
            document.body.addEventListener('click', hideEdit);
        });
        const hideEdit = (event: any) => {
            if (!isEditing.value) return;
                const eventPath = event.composedPath();
                for (let i = 0; i < eventPath.length; i++) {
                const target = eventPath[i];
                if (/tippy-popper/.test(target.className)
                    || /bk-info-box/.test(target.className)) {
                    return;
                }
            }
            isEditing.value = false;
            isLoading.value = true;

            if(HaveSameElements(localValue.value))return;
            emit('editTag', localValue.value);
        }
        const HaveSameElements = (compare: Array<any>) => {
            // 将数组转换为集合
            const set1 = new Set(props.value.map((item :any) => item.className === '' ? item.name : item.className));
            const set2 = new Set(compare);

            // 如果集合的大小不相等，则数组不相同
            if (set1.size !== set2.size) {
                return false;
            }

            // 检查每个元素是否都存在于另一个集合中
            for (let element of set1) {
                if (!set2.has(element)) {
                    return false;
                }
            }

            return true;

        }
        const handleEdit = () => {
            // 关闭其他弹框
            document.body.click();
            isEditing.value = true;
        };

        const handleTextClick = () => {
            // if (!props.shortcut) {
            //     return;
            // }
            handleEdit();
            nextTick(() => {
                // 获取所有带有 stable 类的元素
                const stableAllElements = document.querySelectorAll('.stable');
                stableAllElements?.forEach(el => {
                    const nextSiblingElement = el.nextElementSibling  as HTMLElement;
                    if(nextSiblingElement) {
                        nextSiblingElement.style.display = 'none';
                    }
                });
            });
        };

        const handleCopy = () => {
            if (localValue.value.length < 1) {
                proxy?.$bkMessage({
                    theme: 'warning',
                    message: i18n.t('标签为空'),
                });
                return;
            }
            copyMemo.value = JSON.parse(JSON.stringify(localValue.value));
            copyMemo.value.every((item:any) => !!item.name) && proxy?.$bkMessage({
                theme: 'success',
                message: i18n.t('复制成功'),
            });
        };

        const handlePaste = () => {
            if (copyMemo.value.length < 1) {
                proxy?.$bkMessage({
                    theme: 'warning',
                    message: i18n.t('请先复制标签'),
                });
                return;
            }
            localValue.value = [...new Set([...copyMemo.value])];
            emit('paste', { ...props.value, ...localValue.value });
        };

        // 处理输入值更改时候的option效果
        const handleInputchange = (value: string) => {
            const index = props.options.findIndex((item: any) => (
                item.children.some((child: any) => child.name === value || child.id === value)
            ));
            if (index === -1 && value && !localValue.value.includes(value)) {
                state.popShow = true;
                tag.value = value;
            } else {
                state.popShow = false;
                tag.value = '';
            }
        };
        // 输入框失去焦点
        const handleBlur = () => {
            state.popShow = false;
            tag.value = '';
        }
        const handleChange = (tags: string[]) => {
        }

        const filterData = (filterVal :string, filterKey :string, data: []) => {
            return data.filter((item: Record<string,any>) => item.id.includes(filterVal) || item.name.includes(filterVal));
        }

        // 新建标签
        const createTag = async () => {
            const backup = tag.value;
            tag.value = '';
            state.popShow = false;
            const customLabels: any= props.options.find((item: any) => item.id === 'custom');
            customLabels?.children.push({
                id: backup,
                name: backup,
                className: '',
            });
            // 标签输入框更新标签
            
            !localValue.value.includes(backup) && localValue.value.push(backup);
            const res = await AgentStore.apiPkgCreateTags({ project: props.active, tag_descriptions: [backup] as string[] });
        }
        
        return {
            ...toRefs(state),
            isEditing,
            isLoading,
            localValue,
            flexibleTags,
            tag,
            tagTpl,
            
            handleEdit,
            handleTextClick,
            handleCopy,
            handlePaste,
            handleBlur,
            handleChange,
            filterData,
            handleInputchange,
            createTag,
        };
    }
});
</script>
<style lang="postcss" scoped>
@import "@/css/variable.css";

    .bk-search-select {
        &.is-focus {
            z-index: 9;
        }
    }
    
    .create-tag-pop {
        position: relative;
        cursor: pointer;
        width: 100%;
        margin-top: 4px;
        transition-duration: 325ms;
        height: 40px;
        background: #fff;
        border: 1px solid #DCDEE5;
        box-shadow: 0 2px 6px 0 #0000001a;
        border-radius: 2px;
        z-index: 999;
        .create-tag-box {
            width: 100%;
            height: 32px;
            margin: 4px 0;
            line-height: 32px;
            background: #F5F7FA;
            .create-tag {
                color: #63656E;
                margin-left: 24px;
                font-size: 12px;
                span {
                    color: #3A84FF;
                }
            }
        }
    }
    .pkg-manage-table {
        .flexible-tag-group {
            height: 30px;
        }
        .flexible-tag-group .tag-item, .tag-list .tag {
            &.stable {
                color: #14a568;
                background-color: #e4faf0;
            }
            &.latest {
                color: $primaryFontColor;
                background-color: #edf4ff;
            }
            &.test {
                color: #fe9c00;
                background-color: #fff1db;
            }
        }
    }
    
    @keyframes tag-edit-loading {
        to {
            transform: rotateZ(360deg);
        }
    }
  
    .edit-tag {
        position: relative;
        height: 30px;
        cursor: pointer;
        border-radius: 2px;
        &:hover {
            background: #e1e2e6;
        }
        &.shortcut {
            .render-value-box {
                padding-left: 4px;
            }
            &:hover {
                .shortcut-action-btn {
                    display: flex;
                }
            }
        }
    
        &:hover {
            .tag-normal-box,
            .tag-shortcut-box {
                display: flex;
                opacity: 100%;
                transform: scale(1);
            }
        }
  
        .render-value-box {
            display: flex;
            height: 30px;
            line-height: 30px;
            align-items: center;
        }
    
        .value-text {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: normal;
        }
    
        .tag-normal-box,
        .tag-shortcut-box {
            display: none;
            height: 30px;
            min-width: 24px;
            color: #979ba5;
            opacity: 0%;
            align-items: center;
        }
  
        .tag-shortcut-box {
            padding-right: 6px;
            margin-left: auto;
            font-size: 16px;
            flex: 0 0 42px;
    
            .paste-btn {
                margin-left: 4px;
            }
    
            .shortcut-action-btn {
                align-items: center;
        
                i:hover {
                    color: #3a84ff;
                }
            }
        }
  
        .tag-normal-box {
            font-size: 16px;
            transform: scale(0);
            transition: 0.15s;
            transform-origin: left center;
    
            .edit-action {
                padding: 6px 15px 6px 2px;
                cursor: pointer;
        
                &:hover {
                    color: #3a84ff;
                }
            }
        }
  
        .tag-edit-loading {
            position: absolute;
            top: 9px;
            right: 10px;
            animation: "tag-edit-loading" 1s linear infinite;
        }
  
        .edit-value-box {
            width: 100%;
        }
    }
</style>