import React from 'react';
import { Box, Text } from 'ink';
import DialogFrame from './DialogFrame.js';
import { useAppState } from '../hooks/useAppState.js';

export default function QuestionDialog() {
  const { questionRequest } = useAppState();
  if (!questionRequest) {
    return null;
  }

  const question = questionRequest.questions[questionRequest.questionIndex];
  const options = question.options || [];

  return (
    <DialogFrame
      title={question.header ? `Question: ${question.header}` : 'Question'}
      subtitle={`${questionRequest.questionIndex + 1}/${questionRequest.questions.length}`}
    >
      <Text bold>{question.question}</Text>
      {options.length > 0 ? (
        <Box flexDirection="column" marginTop={1}>
          {options.map((option, index) => {
            const selected = index === questionRequest.optionIndex;
            const checked = question.multiSelect && questionRequest.selectedOptions.includes(option.label);
            return (
              <Box key={`${option.label}-${index}`} flexDirection="column" marginBottom={1}>
                <Box>
                  <Text color={selected ? 'green' : undefined}>{selected ? '>' : ' '}</Text>
                  <Text> </Text>
                  <Text>{checked ? '[x]' : '[ ]'}</Text>
                  <Text> </Text>
                  <Text bold={selected}>{option.label}</Text>
                </Box>
                {option.description && <Text dimColor>{option.description}</Text>}
              </Box>
            );
          })}
        </Box>
      ) : (
        <Box flexDirection="column" marginTop={1}>
          <Text dimColor>Type your answer and press Enter.</Text>
          <Box borderStyle="round" borderColor="gray" paddingX={1}>
            <Text>{questionRequest.textAnswer}</Text>
            <Text backgroundColor="green"> </Text>
          </Box>
        </Box>
      )}
    </DialogFrame>
  );
}
