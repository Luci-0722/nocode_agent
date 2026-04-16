import React from 'react';
import { Box, Text } from 'ink';
import DialogFrame from './DialogFrame.js';
import { useAppState } from '../hooks/useAppState.js';

export default function ModelPicker() {
  const { modelName, modelOptions, modelPickerIndex } = useAppState();

  return (
    <DialogFrame title="Model Picker" subtitle="Up/Down move, Enter select, Esc close">
      {modelOptions.length === 0 && <Text dimColor>No models available.</Text>}
      {modelOptions.map((option, index) => {
        const selected = index === modelPickerIndex;
        const isCurrent = option.name === modelName;
        const isDefault = option.is_default === 'true';
        return (
          <Box key={option.name}>
            <Text color={selected ? 'green' : undefined}>{selected ? '>' : ' '}</Text>
            <Text> </Text>
            <Text bold={selected}>{option.name}</Text>
            <Text dimColor>{` (${option.model})`}</Text>
            {isCurrent && <Text color="green"> current</Text>}
            {isDefault && <Text color="yellow"> default</Text>}
          </Box>
        );
      })}
    </DialogFrame>
  );
}
